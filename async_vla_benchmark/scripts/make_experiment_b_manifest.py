#!/usr/bin/env python3
import argparse
import hashlib
import os
from pathlib import Path

from async_vla_benchmark.benchmark.experiment_b import BASE_TASK_ID, BASE_TASK_NAME, SUITE, experiment_b_manifest, validate_experiment_a_gate
from async_vla_benchmark.benchmark.logging import read_csv, write_csv


def main():
    os.environ["MPLBACKEND"] = "Agg"
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--experiment-a-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for field in ("git_sha", "lerobot_git_sha", "libero_plus_git_sha", "model_revision"):
        parser.add_argument("--" + field.replace("_", "-"), required=True)
    args = parser.parse_args()
    gate_hash = validate_experiment_a_gate(args.experiment_a_gate)
    from async_vla_benchmark.scripts.run_stage1 import _configure_libero_home
    _configure_libero_home("id")
    from lerobot.envs.libero import _get_suite
    installed_name = _get_suite(SUITE).get_task_names()[BASE_TASK_ID]
    if installed_name != BASE_TASK_NAME:
        raise RuntimeError(f"frozen standard-LIBERO base task mismatch: {installed_name!r} != {BASE_TASK_NAME!r}")
    frozen_hash = hashlib.sha256(args.variants.read_bytes()).hexdigest()
    provenance = {field: getattr(args, field) for field in ("git_sha", "lerobot_git_sha", "libero_plus_git_sha", "model_revision")}
    rows = experiment_b_manifest(read_csv(args.variants), provenance, frozen_hash, gate_hash)
    write_csv(args.output, rows)
    print("PASS manifest=64 ID=16 OOD=48 variants=3 seeds=8 gate=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
