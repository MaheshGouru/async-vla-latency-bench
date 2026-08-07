#!/usr/bin/env python3
"""Validate benchmark outputs before figure generation."""

import argparse
import json
import math
import sys
from pathlib import Path


def _load_parquet(path: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required to validate parquet outputs") from exc
    return pd.read_parquet(path).to_dict("records")


_RAW_TIMESTAMP_FIELDS = (
    "observation_capture_time",
    "preprocessing_start_time",
    "preprocessing_end_time",
    "inference_start_time",
    "inference_end_time",
    "postprocessing_end_time",
    "request_complete_time",
)


def _check_request_timestamps(requests: list[dict]) -> list[str]:
    """Check monotonicity of the raw per-stage timestamps, when present.

    Persisted per-episode request records only carry the derived `_ms`
    latency fields (spec section 10's request-provenance schema:
    measured_request_latency_ms, model_latency_ms, etc.) -- the raw absolute
    timestamps this check wants are a `native_latency.csv`-only concern
    (spec section 7), produced by profile_latency.py's dedicated
    measurement pass, not by run_benchmark.py's episode execution. Skip
    gracefully rather than KeyError when a request record doesn't carry them.
    """
    errors = []
    for r in requests:
        if not all(field in r for field in _RAW_TIMESTAMP_FIELDS):
            continue
        times = [(field, r[field]) for field in _RAW_TIMESTAMP_FIELDS]
        for i in range(len(times) - 1):
            if times[i][1] > times[i + 1][1]:
                errors.append(
                    f"request {r['request_id']}: {times[i][0]} ({times[i][1]}) > "
                    f"{times[i + 1][0]} ({times[i + 1][1]})"
                )
    return errors


def _check_delay_conversion(requests: list[dict], control_period_seconds: float) -> list[str]:
    errors = []
    for r in requests:
        total_ms = r["measured_request_latency_ms"] + r["added_latency_ms"]
        # The "ideal" latency profile forces logical delay_steps=0 by design
        # (spec section 8/12), regardless of the measured wall-clock model
        # runtime -- that runtime is still recorded (measured_request_latency_ms)
        # for reference, it just doesn't feed into the ceil() conversion.
        if r.get("latency_profile") == "ideal":
            expected = 0
        else:
            expected = math.ceil(total_ms / (control_period_seconds * 1000.0))
        if expected != r["delay_steps"]:
            errors.append(
                f"request {r['request_id']}: delay_steps {r['delay_steps']} != expected {expected} "
                f"for latency {total_ms:.2f} ms and period {control_period_seconds * 1000:.2f} ms"
            )
    return errors


def _check_action_records(actions: list[dict], chunk_ids: set, request_source_ids: set) -> list[str]:
    errors = []
    for a in actions:
        if a["action_age_steps"] < 0:
            errors.append(f"action {a['control_step']}: negative action age")
        # queue_depth_before == 0 is the expected, correct value for a hold
        # action (the queue ran dry before this step's pop) -- only negative
        # depths are actually invalid.
        if a["queue_depth_before"] < 0 or a["queue_depth_after"] < 0:
            errors.append(f"action {a['control_step']}: invalid queue depth")
        if not a["is_hold_action"]:
            if a["chunk_id"] not in chunk_ids:
                errors.append(f"action {a['control_step']}: references missing chunk {a['chunk_id']}")
            if a["source_observation_id"] not in request_source_ids:
                errors.append(
                    f"action {a['control_step']}: references missing observation {a['source_observation_id']}"
                )
    return errors


def _check_outstanding_overlap(requests: list[dict]) -> list[str]:
    """Ensure at most one request is logically outstanding at any control step.

    Excludes "ideal"-profile requests: they resolve synchronously with zero
    logical delay by design (request_step == response_available_step), which
    includes the naive_async/rtc startup seed request issued and resolved
    before the main control loop begins (see EpisodeRunner.run()). Two
    requests sharing the same request_step -- the synchronous startup seed
    and the first real request -- is expected there, not a concurrency bug;
    the runtime's actual one-outstanding-request invariant is enforced
    directly by ActionQueue.begin_request()'s RuntimeError.
    """
    errors = []
    events = []
    for r in requests:
        if r.get("latency_profile") == "ideal":
            continue
        events.append((r["request_step"], +1, r["request_id"]))
        # No "+1": the request is no longer outstanding *at*
        # response_available_step itself (EpisodeRunner.run()'s loop calls
        # _take_available() before _maybe_request() each iteration, so a
        # response due this step is already resolved before a new request
        # for this same step could be submitted).
        events.append((r["response_available_step"], -1, r["request_id"]))
    # At a tied step, process the resolution (-1) before a new request's
    # start (+1) -- matches the runtime's actual resolve-then-request order
    # within one control_step, so a same-step handoff isn't miscounted as
    # two requests briefly overlapping.
    events.sort(key=lambda x: (x[0], x[1]))
    active = 0
    for step, delta, req_id in events:
        active += delta
        if active > 1:
            errors.append(f"multiple requests outstanding around step {step} (including {req_id})")
            break
    return errors


def _is_missing_chunk_id(chunk_id) -> bool:
    """True for a hold action's absent chunk_id.

    Hold actions store chunk_id=None, but a parquet round-trip through
    pandas/pyarrow's nullable string dtype reads missing values back as
    float('nan'), not None -- `chunk_id is None` alone misses them.
    """
    if chunk_id is None:
        return True
    return isinstance(chunk_id, float) and math.isnan(chunk_id)


def _check_horizon(actions: list[dict], fixed_horizon: int) -> list[str]:
    """Ensure no chunk contributes more than fixed_horizon executed actions in a row."""
    from itertools import groupby

    errors = []
    for chunk_id, group in groupby(actions, key=lambda a: a["chunk_id"]):
        if _is_missing_chunk_id(chunk_id):
            continue
        count = sum(1 for _ in group)
        if count > fixed_horizon:
            errors.append(f"chunk {chunk_id} executed {count} actions > fixed_horizon {fixed_horizon}")
    return errors


def validate_episode(output_dir: Path, episode_id: str, summary: dict) -> list[str]:
    errors = []
    requests_path = output_dir / "requests" / f"{episode_id}.parquet"
    actions_path = output_dir / "actions" / f"{episode_id}.parquet"

    if not requests_path.exists():
        errors.append(f"missing requests parquet for {episode_id}")
    if not actions_path.exists():
        errors.append(f"missing actions parquet for {episode_id}")
    if errors:
        return errors

    requests = _load_parquet(requests_path)
    actions = _load_parquet(actions_path)
    chunk_ids = {r["chunk_id"] for r in requests}
    request_source_ids = {r["source_observation_id"] for r in requests}

    control_period = summary.get("logical_completion_time_seconds", 0.0) / max(summary.get("environment_steps", 1), 1)
    if control_period <= 0:
        # Infer from actions if possible.
        if actions:
            control_period = actions[0]["logical_time_seconds"] / max(actions[0]["control_step"], 1)

    errors.extend(_check_request_timestamps(requests))
    if control_period > 0:
        errors.extend(_check_delay_conversion(requests, control_period))
    errors.extend(_check_action_records(actions, chunk_ids, request_source_ids))
    errors.extend(_check_outstanding_overlap(requests))
    errors.extend(_check_horizon(actions, summary.get("fixed_horizon", 10)))

    # RTC sanity: delay_steps should not be globally averaged (identical across all requests is suspicious).
    if summary.get("strategy") == "rtc" and len(requests) > 1:
        delays = [r["delay_steps"] for r in requests]
        if len(set(delays)) == 1:
            errors.append("RTC requests all have the same delay_steps; expected request-specific delays")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    episodes_dir = args.output_dir / "episodes"
    if not episodes_dir.exists():
        print("no episodes to validate")
        return 1

    all_errors = []
    for path in sorted(episodes_dir.glob("*.json")):
        summary = json.loads(path.read_text())
        episode_id = summary.get("episode_id", path.stem)
        errors = validate_episode(args.output_dir, episode_id, summary)
        if errors:
            all_errors.extend([f"{episode_id}: {e}" for e in errors])
        else:
            print(f"OK {episode_id}")

    if all_errors:
        print("\n".join(all_errors))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
