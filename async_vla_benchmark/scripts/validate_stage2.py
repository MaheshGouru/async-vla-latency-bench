#!/usr/bin/env python3
"""Validate the frozen Stage 2 matrix and request-level diagnostics."""

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.stage2 import ADDED_DELAYS_MS, HORIZONS, SEEDS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    manifest = read_csv(args.manifest)
    errors = []
    if len(manifest) != 360 or len({r["run_id"] for r in manifest}) != 360:
        errors.append("manifest must contain 360 unique rows")
    if {int(r["configured_n_action_steps"]) for r in manifest} != set(HORIZONS): errors.append("wrong horizons")
    if {int(r["added_delay_ms"]) for r in manifest} != set(ADDED_DELAYS_MS): errors.append("wrong delays")
    if {int(r["seed"]) for r in manifest} != set(SEEDS): errors.append("wrong seeds")
    if any(r["execution_method"] != "rtc" or r["scene_condition"] != "id" for r in manifest): errors.append("non-RTC/ID row")
    pair_groups = defaultdict(list)
    for row in manifest:
        pair_groups[(row["task_key"], row["seed"])].append(row)
    if len(pair_groups) != 15: errors.append(f"expected 15 task×seed pairing groups, got {len(pair_groups)}")
    for key, group in pair_groups.items():
        identities = {(
            row.get("initialization_index_or_id", ""),
            row.get("initial_state_fingerprint_method", ""),
            row.get("initial_state_fingerprint", ""),
        ) for row in group}
        cells = {(
            int(row["configured_n_action_steps"]), int(row["added_delay_ms"])
        ) for row in group}
        if len(group) != 24 or cells != {(h, d) for h in HORIZONS for d in ADDED_DELAYS_MS}:
            errors.append(f"{key}: incomplete 24-cell paired block")
        if len(identities) != 1 or any(not value or value.startswith("PENDING_") for value in next(iter(identities), ())):
            errors.append(f"{key}: unresolved or inconsistent initialization identity")
    results_path = args.output_dir / "stage2_local_sensitivity_episode_results.csv"
    results = read_csv(results_path) if results_path.exists() else []
    by_id = {r["run_id"]: r for r in results}
    missing = [r["run_id"] for r in manifest if r["run_id"] not in by_id]
    invalid = [r["run_id"] for r in results if not r.get("status", "").startswith("ok")]
    required_episode = (
        "stage", "analysis_status", "checkpoint_id", "runner_commit", "environment_version",
        "base_task_id", "base_task_name", "task_id", "task_name",
        "initialization_index_or_id", "initial_state_fingerprint", "initial_state_fingerprint_method",
        "configured_n_action_steps", "prediction_horizon_actions", "rtc_execution_horizon",
        "request_threshold_actions", "control_period_ms", "request_latency_mean_ms",
        "logical_delay_steps_mean", "coverage_ratio_added", "coverage_ratio_total_mean",
        "rtc_mean_frozen_prefix_steps", "rtc_mean_guided_overlap_steps",
        "rtc_mean_fresh_suffix_steps", "environment_fingerprint",
    )
    required_request = (
        "measured_request_latency_ms", "added_latency_ms", "total_logical_latency_ms",
        "logical_delay_steps", "configured_n_action_steps", "prediction_horizon_actions",
        "rtc_configured_execution_horizon", "request_threshold_actions",
        "control_period_ms", "coverage_ratio_added", "coverage_ratio_total",
        "rtc_frozen_prefix_steps", "rtc_guided_overlap_steps", "rtc_fresh_suffix_steps",
        "rtc_inference_delay_steps", "rtc_inference_delay_error_steps",
        "previous_chunk_remaining_at_request", "previous_chunk_remaining_at_response",
    )
    try:
        import pandas as pd
    except ImportError:
        pd = None
        errors.append("pandas is required for request-artifact validation")
    for plan in manifest:
        run_id = plan["run_id"]
        if run_id not in by_id:
            continue
        result = by_id[run_id]
        for field in required_episode:
            if result.get(field, "") == "": errors.append(f"{run_id}: missing {field}")
        if int(result["configured_n_action_steps"]) != int(plan["configured_n_action_steps"]): errors.append(f"{run_id}: horizon mismatch")
        for field in ("initialization_index_or_id", "initial_state_fingerprint", "initial_state_fingerprint_method"):
            if result.get(field) != plan.get(field): errors.append(f"{run_id}: {field} mismatch")
        request_path = args.output_dir / "requests" / f"{run_id}.parquet"
        if not request_path.exists():
            errors.append(f"{run_id}: missing request artifact")
        elif pd is not None:
            frame = pd.read_parquet(request_path)
            for field in required_request:
                if field not in frame.columns: errors.append(f"{run_id}: request artifact missing {field}")
            measured = frame[frame["latency_profile"] != "ideal"] if "latency_profile" in frame else frame.iloc[1:]
            if measured.empty: errors.append(f"{run_id}: no non-startup requests")
            elif all(field in measured.columns for field in required_request):
                required_nonnull = [field for field in required_request if field != "previous_chunk_remaining_at_response"]
                if measured[required_nonnull].isnull().any().any(): errors.append(f"{run_id}: null required request diagnostic")
                horizon = int(plan["configured_n_action_steps"])
                for index, request in measured.iterrows():
                    expected_steps = math.ceil(float(request["total_logical_latency_ms"]) / float(request["control_period_ms"]))
                    if int(request["logical_delay_steps"]) != expected_steps:
                        errors.append(f"{run_id}: request {index} logical delay does not use ceil(total/control period)")
                    if int(request["configured_n_action_steps"]) != horizon:
                        errors.append(f"{run_id}: request {index} configured horizon mismatch")
                    if int(request["rtc_configured_execution_horizon"]) != horizon:
                        errors.append(f"{run_id}: request {index} RTC horizon mismatch")
                    if int(request["request_threshold_actions"]) != horizon:
                        errors.append(f"{run_id}: request {index} threshold mismatch")
                    expected_ratio = expected_steps / horizon
                    if not math.isclose(float(request["coverage_ratio_total"]), expected_ratio, rel_tol=0, abs_tol=1e-9):
                        errors.append(f"{run_id}: request {index} total coverage ratio mismatch")
        episode_path = args.output_dir / "episodes" / f"{run_id}.json"
        if not episode_path.exists(): errors.append(f"{run_id}: missing episode artifact")
        else:
            try: json.loads(episode_path.read_text())
            except Exception: errors.append(f"{run_id}: invalid episode JSON")
    if missing and not args.allow_incomplete: errors.append(f"{len(missing)} missing result rows")
    if invalid: errors.append(f"{len(invalid)} invalid result rows")
    print(f"manifest=360 results={len(results)} missing={len(missing)} invalid={len(invalid)}")
    if errors:
        for error in errors: print(f"ERROR: {error}")
        return 1
    print("Stage 2 validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
