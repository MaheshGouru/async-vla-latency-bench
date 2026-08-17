#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from async_vla_benchmark.benchmark.experiment_b import validate_experiment_a_gate
from async_vla_benchmark.benchmark.logging import read_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--experiment-a-gate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); errors = []
    gate_hash = validate_experiment_a_gate(args.experiment_a_gate)
    rows = read_csv(args.manifest)
    if len(rows) != 8 or {row["seed"] for row in rows} != {"999"}:
        errors.append("smoke manifest must contain 8 seed-999 rows")
    if {row.get("experiment_a_dispatch_gate_sha256") for row in rows} != {gate_hash}:
        errors.append("smoke manifest does not consume the passing Experiment A gate")
    result_path = args.output_dir / "experiment_b_episode_results.csv"
    results = read_csv(result_path) if result_path.exists() else []; by_id = {row["run_id"]: row for row in results}
    for row in rows:
        result = by_id.get(row["run_id"])
        if not result or not result.get("status", "").startswith("ok"):
            errors.append(f"{row['run_id']}: missing/invalid result")
        for folder, extension in (("episodes", "json"), ("requests", "parquet"), ("actions", "parquet")):
            if not (args.output_dir / folder / f"{row['run_id']}.{extension}").exists():
                errors.append(f"{row['run_id']}: missing {folder}")
    report = {"status": "pass" if not errors else "fail", "episodes": len(rows), "seed": 999, "analysis_seeds_used": False, "experiment_a_dispatch_gate_sha256": gate_hash, "errors": errors}
    (args.output_dir / "experiment_b_smoke_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if errors:
        print(*(f"ERROR: {error}" for error in errors), sep="\n"); return 1
    print("PASS: 8 seed-999 Experiment B smoke episodes; no analysis seeds used; Experiment A gate verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
