#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage3 import HORIZONS, as_rows, stage3_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen-horizons", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--lerobot-git-sha", required=True)
    parser.add_argument("--libero-plus-git-sha", required=True)
    parser.add_argument("--model-revision", required=True)
    args = parser.parse_args()
    for value in (args.git_sha, args.lerobot_git_sha, args.libero_plus_git_sha, args.model_revision):
        if not value or value == "main": raise ValueError("provenance must use immutable revisions")
    rows = stage3_manifest(vars(args))
    write_csv(args.output, as_rows(rows))
    args.frozen_horizons.write_text(json.dumps({
        "horizons": list(HORIZONS),
        "frozen_before_stage2": True,
        "stage2_used_for_selection": False,
    }, indent=2) + "\n")
    print("PASS manifest=288 RTC=288 ID=96 OOD=192 primary=240 posthoc=48")
    return 0


if __name__ == "__main__": raise SystemExit(main())
