#!/usr/bin/env python3
"""Deterministically freeze the three Experiment B object-layout variants."""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

from async_vla_benchmark.benchmark.experiment_b import SUITE, select_variant_entries, validate_experiment_a_gate
from async_vla_benchmark.benchmark.ood_tasks import find_task_classification_path


def main():
    os.environ["MPLBACKEND"] = "Agg"
    native = Path.home() / "stage1-native"
    if native.exists() and os.environ.get("EXPERIMENT_B_NATIVE_REEXEC") != str(native):
        env = os.environ.copy()
        env.update({
            "EXPERIMENT_B_NATIVE_REEXEC": str(native), "MAGICK_HOME": str(native),
            "PATH": str(native / "bin") + os.pathsep + env.get("PATH", ""),
            "LD_LIBRARY_PATH": str(native / "lib") + os.pathsep + env.get("LD_LIBRARY_PATH", ""),
        })
        os.execve(sys.executable, [sys.executable, "-m", "async_vla_benchmark.scripts.resolve_experiment_b_variants", *sys.argv[1:]], env)
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-a-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gate_hash = validate_experiment_a_gate(args.experiment_a_gate)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite frozen variants: {args.output}")
    classification_path = find_task_classification_path()
    root = classification_path.parent.parent
    config = Path.home() / ".libero/config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f"assets: {root/'assets'}\nbddl_files: {root/'bddl_files'}\ndatasets: {root/'../datasets'}\ninit_states: {root/'init_files'}\n")
    from wand.api import library as _wand_library  # noqa: F401
    from lerobot.envs.libero import _get_suite
    task_names = _get_suite(SUITE).get_task_names()
    entries = json.loads(classification_path.read_text())[SUITE]
    rows = select_variant_entries(entries, task_names)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(*[f"{row['classification_id']},{row['api_task_index']},L{row['difficulty_level']},{row['variant_name']}" for row in rows], sep="\n")
    print("PASS frozen_variants=3 gate_sha256", gate_hash, "variants_sha256", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
