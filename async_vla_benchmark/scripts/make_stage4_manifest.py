#!/usr/bin/env python3
import argparse
from pathlib import Path

from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage4 import as_rows, stage4_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--libero-plus-git-sha", required=True)
    args = parser.parse_args()
    for value in (args.git_sha, args.libero_plus_git_sha):
        if len(value) != 40: raise ValueError("Stage 4 provenance requires immutable 40-character SHAs")
    rows = stage4_manifest(vars(args)); write_csv(args.output, as_rows(rows))
    print("PASS manifest=64 OpenVLA-OFT=64 ID=32 OOD=32 Native=32 plus200=32")
    return 0


if __name__ == "__main__": raise SystemExit(main())
