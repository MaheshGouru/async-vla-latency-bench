#!/usr/bin/env python3
"""Materialize the frozen 480-row Stage 1 analysis manifest."""

import argparse
import csv
from pathlib import Path

from async_vla_benchmark.benchmark.stage1 import (
    ResolvedVariant,
    load_selected_delay,
    stage1_manifest,
    write_dataclass_csv,
)


def _variants(path: Path) -> list[ResolvedVariant]:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    return [ResolvedVariant(
        task_key=r["task_key"], suite=r["suite"], base_task_id=int(r["base_task_id"]),
        base_task_name=r["base_task_name"], task_group=r["task_group"],
        perturbation_key=r["perturbation_key"], official_category=r["official_category"],
        mechanism_group=r["mechanism_group"], classification_id=int(r["classification_id"]),
        api_task_index=int(r["api_task_index"]), variant_name=r["variant_name"],
        difficulty_level=int(r["difficulty_level"]),
    ) for r in rows]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--selected-delay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--lerobot-git-sha", required=True)
    parser.add_argument("--libero-plus-git-sha", required=True)
    parser.add_argument("--model-revision", required=True)
    args = parser.parse_args()
    provenance = {
        "git_sha": args.git_sha,
        "lerobot_git_sha": args.lerobot_git_sha,
        "libero_plus_git_sha": args.libero_plus_git_sha,
        "model_revision": args.model_revision,
    }
    if any(not value or value == "main" for value in provenance.values()):
        raise ValueError("all provenance fields must be immutable revisions, not 'main'")
    plans = stage1_manifest(
        _variants(args.variants), load_selected_delay(args.selected_delay), provenance
    )
    write_dataclass_csv(args.output, plans)
    print(f"wrote {len(plans)} rows: 420 OOD, 36 new ID, 24 reused Stage 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
