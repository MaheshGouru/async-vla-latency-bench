#!/usr/bin/env python3
"""Validate Stage 1 manifest coverage and completed episode artifacts."""

import argparse
from collections import Counter
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    manifest = read_csv(args.manifest)
    errors = []
    if len(manifest) != 480 or len({r["run_id"] for r in manifest}) != 480:
        errors.append("manifest must contain 480 unique rows")
    counts = Counter(r["scene_condition"] for r in manifest)
    if counts != {"id": 60, "ood": 420}:
        errors.append(f"wrong scene counts: {dict(counts)}")
    if sum(r["reuse_stage0"].lower() == "true" for r in manifest) != 24:
        errors.append("expected 24 Stage 0 reuse rows")
    if {r["seed"] for r in manifest} != {"0", "1", "2", "3", "4"}:
        errors.append("wrong seed set")
    if any(r["n_action_steps"] != "25" for r in manifest): errors.append("non-25 action horizon")
    if any(int(r["added_delay_ms"]) != (0 if r["delay_condition"] == "low" else 200) for r in manifest): errors.append("delay mismatch")
    result_path = args.output_dir / "stage1_episode_results.csv"
    results = read_csv(result_path) if result_path.exists() else []
    by_id = {r["run_id"]: r for r in results}
    missing = [r["run_id"] for r in manifest if r["run_id"] not in by_id]
    invalid = [r["run_id"] for r in results if not r.get("status", "").startswith("ok")]
    required_metrics = (
        "request_latency_mean_ms", "request_latency_p50_ms", "request_latency_p95_ms",
        "action_age_mean_ms", "action_age_p50_ms", "action_age_p95_ms", "action_age_max_ms",
        "logical_delay_steps_mean", "logical_delay_steps_p95", "queue_occupancy_mean",
        "queue_occupancy_p95", "underrun_count", "hold_count", "discard_count",
        "num_policy_requests", "wall_clock_episode_s", "gpu_id",
    )
    for row in manifest:
        if row["run_id"] not in by_id: continue
        result = by_id[row["run_id"]]
        for field in ("task_key", "scene_condition", "execution_method", "delay_condition", "seed", "variant_name"):
            if result.get(field) != row[field]: errors.append(f"{row['run_id']}: {field} mismatch")
        for field in required_metrics:
            if result.get(field, "") == "": errors.append(f"{row['run_id']}: missing metric {field}")
        if result.get("source") == "stage0_reuse_unverified_identity":
            if any(result.get(field) for field in ("git_sha", "lerobot_git_sha", "model_revision", "environment_fingerprint")):
                errors.append(f"{row['run_id']}: reused row falsely claims verified Stage 0 identity")
        elif any(not result.get(field) for field in ("git_sha", "lerobot_git_sha", "model_revision", "environment_fingerprint")):
            errors.append(f"{row['run_id']}: new Stage 1 row missing immutable identity")
    if missing and not args.allow_incomplete: errors.append(f"{len(missing)} missing result rows")
    if invalid: errors.append(f"{len(invalid)} invalid result rows")
    print(f"manifest=480 results={len(results)} missing={len(missing)} invalid={len(invalid)}")
    if errors:
        for error in errors: print(f"ERROR: {error}")
        return 1
    print("Stage 1 validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
