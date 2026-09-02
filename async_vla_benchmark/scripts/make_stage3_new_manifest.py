#!/usr/bin/env python3
"""Generate the Stage 3 New 1,944-row manifest (or an 18-row smoke manifest)."""
from __future__ import annotations
import argparse
from pathlib import Path

from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage3_new import (
    CANDIDATES, HORIZONS, SEEDS, as_rows, stage3_new_manifest,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    p.add_argument("--lerobot-git-sha", required=True)
    p.add_argument("--libero-plus-git-sha", required=True)
    p.add_argument("--model-revision", required=True)
    p.add_argument("--smoke-seed", type=int, default=None,
                   help="Single seed for smoke run (e.g. 999); omit for full run")
    p.add_argument("--smoke-horizon", type=int, default=25,
                   help="Single horizon for smoke run (default 25)")
    args = p.parse_args()

    for value in (args.git_sha, args.lerobot_git_sha,
                  args.libero_plus_git_sha, args.model_revision):
        if not value or value == "main":
            raise ValueError("All provenance arguments must be immutable SHA revisions")

    provenance = {
        "git_sha": args.git_sha,
        "lerobot_git_sha": args.lerobot_git_sha,
        "libero_plus_git_sha": args.libero_plus_git_sha,
        "model_revision": args.model_revision,
    }

    rows = stage3_new_manifest(
        provenance,
        smoke_seed=args.smoke_seed,
        smoke_horizon=args.smoke_horizon if args.smoke_seed is not None else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, as_rows(rows))

    if args.smoke_seed is not None:
        n_id  = sum(1 for r in rows if r.scene == "id")
        n_ood = sum(1 for r in rows if r.scene == "ood")
        print(f"PASS smoke manifest: {len(rows)} rows "
              f"(ID={n_id} OOD={n_ood}) seed={args.smoke_seed} h={args.smoke_horizon}")
    else:
        print(
            f"PASS manifest={len(rows)} "
            f"RTC={len(rows)} "
            f"ID={sum(1 for r in rows if r.scene == 'id')} "
            f"OOD={sum(1 for r in rows if r.scene == 'ood')} "
            f"candidates={len(CANDIDATES)} "
            f"horizons={list(HORIZONS)} "
            f"seeds={min(SEEDS)}..{max(SEEDS)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
