#!/usr/bin/env python3
"""Make the Stage 5A ID-only coverage-calibration manifest from the 5A0 audit."""
import argparse
import json
from pathlib import Path

from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage5 import as_rows, stage5a_manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    p.add_argument("--libero-plus-git-sha", required=True)
    args = p.parse_args()

    for value in (args.git_sha, args.libero_plus_git_sha):
        if len(value) != 40:
            raise ValueError("Stage 5 provenance requires immutable 40-character SHAs")

    audit = json.loads(args.audit.read_text())
    if not audit.get("coverage_sweep_gt_native_allowed", False):
        # Gate is closed; the manifest must remain empty so no 5A rollout is issued.
        write_csv(args.output, [])
        print("PASS empty Stage 5A manifest: 5A0 gate is closed (native coverage fixed at 8)")
        return 0

    allowed = audit.get("allowed_candidate_coverages_after_audit", [8])
    if any(c > audit.get("maximum_native_coverage", 8) for c in allowed):
        raise ValueError("audit disallows a coverage above the verified native horizon")

    rows = stage5a_manifest({"git_sha": args.git_sha, "libero_plus_git_sha": args.libero_plus_git_sha}, allowed)
    write_csv(args.output, as_rows(rows))
    print(f"PASS manifest={len(rows)} Stage 5A rows coverages={sorted(set(r.configured_action_coverage for r in rows))}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
