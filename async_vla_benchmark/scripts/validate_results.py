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


def _check_request_timestamps(requests: list[dict]) -> list[str]:
    errors = []
    for r in requests:
        times = [
            ("observation_capture_time", r["observation_capture_time"]),
            ("preprocessing_start_time", r["preprocessing_start_time"]),
            ("preprocessing_end_time", r["preprocessing_end_time"]),
            ("inference_start_time", r["inference_start_time"]),
            ("inference_end_time", r["inference_end_time"]),
            ("postprocessing_end_time", r["postprocessing_end_time"]),
            ("request_complete_time", r["request_complete_time"]),
        ]
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
        if a["queue_depth_before"] < 1 or a["queue_depth_after"] < 0:
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
    """Ensure at most one request is logically outstanding at any control step."""
    errors = []
    events = []
    for r in requests:
        events.append((r["request_step"], +1, r["request_id"]))
        events.append((r["response_available_step"] + 1, -1, r["request_id"]))
    events.sort(key=lambda x: (x[0], -x[1]))
    active = 1
    for step, delta, req_id in events:
        active += delta
        if active > 1:
            errors.append(f"multiple requests outstanding around step {step} (including {req_id})")
            break
    return errors


def _check_horizon(actions: list[dict], fixed_horizon: int) -> list[str]:
    """Ensure no chunk contributes more than fixed_horizon executed actions in a row."""
    from itertools import groupby

    errors = []
    for chunk_id, group in groupby(actions, key=lambda a: a["chunk_id"]):
        if chunk_id is None:
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
