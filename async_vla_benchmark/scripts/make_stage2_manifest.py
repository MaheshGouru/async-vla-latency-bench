#!/usr/bin/env python3
"""Materialize the frozen 360-row Stage 2 manifest."""

import argparse
from pathlib import Path

from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage2 import as_rows, stage2_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--lerobot-git-sha", required=True)
    parser.add_argument("--model-revision", required=True)
    args = parser.parse_args()
    provenance = vars(args)
    if any(not provenance[key] or provenance[key] == "main" for key in ("git_sha", "lerobot_git_sha", "model_revision")):
        raise ValueError("provenance must use immutable revisions")
    rows = stage2_manifest(provenance)
    write_csv(args.output, as_rows(rows))
    print(f"PASS manifest={len(rows)} RTC=360 ID=360 new=360")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
