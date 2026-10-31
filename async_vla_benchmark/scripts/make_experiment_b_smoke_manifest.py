#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path

from async_vla_benchmark.benchmark.experiment_b import _plan, validate_experiment_a_gate, validate_frozen_variants
from async_vla_benchmark.benchmark.logging import read_csv, write_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--experiment-a-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for field in ("git_sha", "lerobot_git_sha", "libero_plus_git_sha", "model_revision"):
        parser.add_argument("--" + field.replace("_", "-"), required=True)
    args = parser.parse_args()
    gate_hash = validate_experiment_a_gate(args.experiment_a_gate)
    variants = read_csv(args.variants); validate_frozen_variants(variants)
    frozen_hash = hashlib.sha256(args.variants.read_bytes()).hexdigest()
    provenance = {field: getattr(args, field) for field in ("git_sha", "lerobot_git_sha", "libero_plus_git_sha", "model_revision")}
    rows = []
    for delay in (0, 200):
        rows.append(_plan(provenance, None, "id", delay, 999, frozen_hash, gate_hash))
    for variant in variants:
        for delay in (0, 200):
            rows.append(_plan(provenance, variant, "ood", delay, 999, frozen_hash, gate_hash))
    for row in rows:
        row["run_id"] += "__smoke"; row["output_path"] = f"episodes/{row['run_id']}.json"
    write_csv(args.output, rows)
    print("PASS smoke_manifest=8 seed=999 variants=3 analysis_seeds_used=0 gate=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
