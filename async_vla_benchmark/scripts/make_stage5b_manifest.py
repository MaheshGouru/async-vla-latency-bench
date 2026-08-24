#!/usr/bin/env python3
"""Make the Stage 5B conditional OOD × delay manifest from the frozen 5A operating point."""
import argparse
import json
from pathlib import Path

from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage5 import as_rows, stage5b_manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--selected", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    p.add_argument("--libero-plus-git-sha", required=True)
    args = p.parse_args()

    for value in (args.git_sha, args.libero_plus_git_sha):
        if len(value) != 40:
            raise ValueError("Stage 5 provenance requires immutable 40-character SHAs")

    selected = json.loads(args.selected.read_text())
    if not selected.get("proceed_to_stage5b", False):
        write_csv(args.output, [])
        print("PASS empty Stage 5B manifest: 5A operating point does not warrant a rerun")
        return 0

    coverage = int(selected["configured_action_coverage"])
    rows = stage5b_manifest(
        {"git_sha": args.git_sha, "libero_plus_git_sha": args.libero_plus_git_sha},
        coverage,
    )
    write_csv(args.output, as_rows(rows))
    print(f"PASS manifest={len(rows)} Stage 5B rows coverage={coverage}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
