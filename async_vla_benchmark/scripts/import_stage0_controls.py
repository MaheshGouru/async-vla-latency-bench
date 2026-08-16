#!/usr/bin/env python3
"""Import the 24 accepted Stage 0 seed-0/1 controls into Stage 1 analysis."""

import argparse
import csv
import shutil
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv, write_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--stage0-dir", type=Path, required=True)
    parser.add_argument("--stage1-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = [r for r in read_csv(args.manifest) if r["reuse_stage0"].lower() == "true"]
    if len(manifest) != 24:
        raise ValueError(f"expected 24 reuse rows, got {len(manifest)}")
    source_rows = {r["run_id"]: r for r in read_csv(args.stage0_dir / "latency_calibration_episode_results.csv")}
    output_rows = []
    for plan in manifest:
        source_id = plan["source_run_id"]
        if source_id not in source_rows:
            raise FileNotFoundError(f"missing Stage 0 result {source_id}")
        source = source_rows[source_id]
        if source.get("status") != "ok":
            raise ValueError(f"Stage 0 source is not ok: {source_id}")
        for folder, suffix in (("episodes", ".json"), ("requests", ".parquet"), ("actions", ".parquet")):
            src = args.stage0_dir / folder / f"{source_id}{suffix}"
            dst = args.stage1_dir / "stage0_reuse" / folder / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        output_rows.append({
            **{key: plan.get(key, "") for key in (
                "run_id", "git_sha", "lerobot_git_sha", "libero_plus_git_sha", "model_revision",
                "task_key", "suite", "base_task_id", "base_task_name", "task_group", "scene_condition",
                "perturbation_key", "official_category", "mechanism_group", "classification_id",
                "api_task_index", "variant_name", "difficulty_level", "execution_method",
                "delay_condition", "added_delay_ms", "seed", "n_action_steps",
            )},
            "success": source["success"], "episode_steps": source["episode_steps"],
            "completion_fraction": source["completion_fraction"], "failure_mode": "success" if source["success"] == "1" else "other",
            "failure_notes": "Imported from Stage 0; immutable runtime identity unavailable",
            "request_latency_mean_ms": source["request_latency_mean_ms"], "request_latency_p50_ms": source["request_latency_p50_ms"],
            "request_latency_p95_ms": source["request_latency_p95_ms"], "action_age_mean_ms": source["action_age_mean_ms"],
            "action_age_p50_ms": source["action_age_p50_ms"], "action_age_p95_ms": source["action_age_p95_ms"],
            "action_age_max_ms": source["action_age_max_ms"], "logical_delay_steps_mean": source["logical_delay_steps_mean"],
            "logical_delay_steps_p95": source["logical_delay_steps_p95"], "queue_occupancy_mean": source["queue_occupancy_mean"],
            "queue_occupancy_p95": source["queue_occupancy_p95"], "underrun_count": source["underrun_count"],
            "hold_count": source["hold_count"], "discard_count": source["discard_count"],
            "num_policy_requests": source["num_policy_requests"], "action_delta_mean": source["action_delta_mean"],
            "action_accel_mean": source["action_accel_mean"], "action_jerk_mean": source["action_jerk_mean"],
            "wall_clock_episode_s": source["wall_clock_episode_s"], "gpu_id": source["gpu_id"],
            "gpu_peak_memory_mb": "", "source": "stage0_reuse_unverified_identity", "status": "ok_with_provenance_limitation",
            "invalid_reason": "",
            # Never make the imported episode look as if it ran under the new
            # Stage 1 revisions. Those Stage 0 identities are genuinely unknown.
            "git_sha": "", "lerobot_git_sha": "", "libero_plus_git_sha": "",
            "model_revision": "", "environment_fingerprint": "",
        })
    result_path = args.stage1_dir / "stage1_episode_results.csv"
    existing = {r["run_id"]: r for r in read_csv(result_path)} if result_path.exists() else {}
    existing.update({r["run_id"]: r for r in output_rows})
    write_csv(result_path, [existing[key] for key in sorted(existing)])
    print(f"imported 24 Stage 0 controls into {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
