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


def _check_terminal_result(summary: dict, actions: list[dict]) -> list[str]:
    """Spec §21: fail when an episode is missing its terminal result.

    A completed episode must record how it ended: a boolean `success`, a
    boolean `timed_out`, and a positive `environment_steps` backed by at least
    one executed action. A crashed or truncated run leaves one of these absent
    or null, which would otherwise be silently aggregated as a failure.
    """
    errors = []
    for field in ("success", "timed_out"):
        if summary.get(field) is None:
            errors.append(f"missing terminal result: {field} is absent or null")
        elif not isinstance(summary[field], bool):
            errors.append(f"terminal result {field} is {summary[field]!r}, expected a bool")
    steps = summary.get("environment_steps")
    if not isinstance(steps, int) or steps <= 0:
        errors.append(f"missing terminal result: environment_steps is {steps!r}")
    elif not actions:
        errors.append(f"episode reports {steps} environment steps but recorded no actions")
    return errors


def _check_cuda_timing_synchronized(requests: list[dict]) -> list[str]:
    """Spec §21: fail when CUDA timing is measured without synchronization.

    Requests recorded on CUDA carry `gpu_event_ms` (from CUDA events read after
    a synchronize) and `cuda_synchronized`. An unsynchronized read races the
    still-running kernels and reports a GPU time far below the wall-clock model
    latency, so a present-but-unflagged or implausible event time is an error.

    Records predating these fields are skipped rather than failed -- the same
    graceful-skip precedent as `_check_request_timestamps` -- so episodes from
    earlier runs stay validatable.
    """
    errors = []
    for r in requests:
        if "cuda_synchronized" not in r and "gpu_event_ms" not in r:
            continue
        gpu_ms = r.get("gpu_event_ms")
        if gpu_ms is None:
            # Ran off CUDA; nothing to synchronize.
            continue
        if not r.get("cuda_synchronized"):
            errors.append(
                f"request {r['request_id']}: gpu_event_ms recorded without synchronization"
            )
        if gpu_ms <= 0:
            errors.append(f"request {r['request_id']}: nonpositive gpu_event_ms {gpu_ms}")
        elif gpu_ms > r["model_latency_ms"]:
            # Wall-clock brackets the GPU work; GPU time exceeding it means the
            # events were not read after a synchronize.
            errors.append(
                f"request {r['request_id']}: gpu_event_ms {gpu_ms:.2f} exceeds wall-clock "
                f"model_latency_ms {r['model_latency_ms']:.2f}"
            )
    return errors


def _check_rtc_inference_delay(summary: dict, requests: list[dict]) -> list[str]:
    """Spec section 21: fail when RTC receives a global average delay.

    The value spec section 15 constrains is `inference_delay` -- what RTC is handed
    at call time -- not `delay_steps`, which is recomputed from the measured latency
    after the call returns. Those are different numbers, so the older check below
    (realized delays all identical) cannot see this class of defect at all: when
    `inference_delay` was hardcoded to 0 on every request, all 222 episodes still
    validated clean. This one reads `rtc_inference_delay_steps`, the logged argument.

    Two failure shapes:
      * a constant `inference_delay` while the realized delays vary -- the signature
        of an average or any other request-independent value;
      * a zero `inference_delay` on a request that actually arrived late, which is
        the specific pre-fix bug.

    Records predating the field are skipped rather than failed, matching
    `_check_request_timestamps`, so earlier episodes stay validatable.
    """
    if summary.get("strategy") != "rtc":
        return []
    logged = [r for r in requests if r.get("rtc_inference_delay_steps") is not None]
    if not logged:
        return []

    errors = []
    for r in logged:
        passed = r["rtc_inference_delay_steps"]
        if passed < 0:
            errors.append(f"request {r['request_id']}: negative rtc_inference_delay_steps {passed}")
        elif passed == 0 and r["delay_steps"] > 0:
            errors.append(
                f"request {r['request_id']}: RTC received inference_delay=0 but the request "
                f"arrived {r['delay_steps']} steps late"
            )

    realized = {r["delay_steps"] for r in logged}
    if len(logged) > 1 and len({r["rtc_inference_delay_steps"] for r in logged}) == 1 and len(realized) > 1:
        errors.append(
            f"RTC received a constant inference_delay "
            f"({logged[0]['rtc_inference_delay_steps']}) across {len(logged)} requests whose "
            f"realized delay_steps vary ({sorted(realized)}); expected a request-specific value"
        )
    return errors


def _check_rtc_action_counts(summary: dict, requests: list[dict]) -> list[str]:
    """Spec section 15.7: fail when the overlapping/guided action counts are unusable.

    These counts are the only direct evidence that guidance did anything, so an
    absent or self-inconsistent record makes an RTC episode uninterpretable rather
    than merely under-documented. Pre-field records are skipped as elsewhere.
    """
    if summary.get("strategy") != "rtc":
        return []
    errors = []
    for r in requests:
        if r.get("rtc_overlap_actions") is None:
            continue
        overlap = r["rtc_overlap_actions"]
        effective = r["rtc_effective_execution_horizon"]
        frozen = r["rtc_frozen_prefix_actions"]
        guided = r["rtc_guided_actions"]
        if min(overlap, effective, frozen, guided) < 0:
            errors.append(f"request {r['request_id']}: negative RTC action count")
        if effective > overlap:
            errors.append(
                f"request {r['request_id']}: effective execution horizon {effective} exceeds "
                f"the {overlap}-action overlap it is clamped to"
            )
        if frozen + guided != effective:
            errors.append(
                f"request {r['request_id']}: frozen {frozen} + guided {guided} != effective "
                f"execution horizon {effective}"
            )
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
    errors.extend(_check_terminal_result(summary, actions))
    errors.extend(_check_cuda_timing_synchronized(requests))
    errors.extend(_check_rtc_inference_delay(summary, requests))
    errors.extend(_check_rtc_action_counts(summary, requests))

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
