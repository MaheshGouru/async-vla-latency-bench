#!/usr/bin/env python3
"""Resolve and freeze the 21 Stage 1 LIBERO-Plus variants."""

import argparse
import json
from pathlib import Path

from async_vla_benchmark.benchmark.ood_tasks import find_task_classification_path
from async_vla_benchmark.benchmark.stage0 import STAGE0_TASKS
from async_vla_benchmark.benchmark.stage1 import resolve_variants, write_dataclass_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"refusing to overwrite frozen mapping: {args.output}")

    # LIBERO prompts with input() when this file is absent, which fails in a
    # detached/Jupyter subprocess. Resolve the pinned clone without importing
    # libero.libero first, then create the same config as the container image.
    classification_path = find_task_classification_path()
    root = classification_path.parent.parent
    config = Path.home() / ".libero" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        f"assets: {root / 'assets'}\n"
        f"bddl_files: {root / 'bddl_files'}\n"
        f"datasets: {root / '../datasets'}\n"
        f"init_states: {root / 'init_files'}\n"
    )

    from lerobot.envs.libero import _get_suite

    classification = json.loads(classification_path.read_text())
    suite_names = {}
    for suite_name in sorted({task.suite for task in STAGE0_TASKS}):
        suite = _get_suite(suite_name)
        suite_names[suite_name] = list(suite.get_task_names())
    rows = resolve_variants(classification, suite_names)
    write_dataclass_csv(args.output, rows)
    print(f"wrote {len(rows)} frozen variants to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
