#!/usr/bin/env python3
"""Create frozen, reviewable follow-up manifests for the CVPR plan.

This script creates *protocol manifests only*. It never imports a policy,
starts a simulator, changes an existing experiment, or launches a GPU job.
The resulting CSVs make the four proposed strengthening steps auditable:

1. coverage/queue mechanism analysis;
2. a coverage-matched second-policy diagnostic;
3. a coverage-aware controller ablation;
4. a broader delay/held-out robustness sweep.

The second-policy and controller rows are intentionally marked ``planned``;
they must not be reported as completed until a separately frozen runner and
validated outputs exist.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _write(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    policy_rows = []
    for policy in ("pi05", "openvla_oft"):
        for task in ("spatial_transport", "goal_drawer"):
            for delay in (0, 200):
                policy_rows.append({
                    "step": "2_second_policy",
                    "status": "planned",
                    "policy": policy,
                    "task": task,
                    "perturbation": "object_layout",
                    "coverage": "policy_calibrated",
                    "delay_ms": delay,
                    "seeds": "fresh_block_to_be_frozen",
                    "execution": "policy_compatible_async",
                })
    _write(output_dir / "second_policy_protocol.csv", policy_rows,
           ["step", "status", "policy", "task", "perturbation",
            "coverage", "delay_ms", "seeds", "execution"])

    controller_rows = []
    for target in ("low_headroom", "medium_headroom", "high_headroom"):
        for delay in (0, 100, 200, 300):
            controller_rows.append({
                "step": "3_controller_ablation",
                "status": "planned",
                "controller": "fixed_coverage_baseline",
                "target_headroom": target,
                "delay_ms": delay,
                "task_split": "ID_calibration_then_held_out_OOD",
                "seeds": "fresh_block_to_be_frozen",
            })
    _write(output_dir / "coverage_controller_protocol.csv", controller_rows,
           ["step", "status", "controller", "target_headroom", "delay_ms",
            "task_split", "seeds"])

    sweep_rows = []
    for task in ("spatial_transport", "goal_drawer", "long_stove_moka"):
        for horizon in (15, 20, 25, 30, 35):
            for delay in (0, 100, 200, 300, 400):
                sweep_rows.append({
                    "step": "4_broader_robustness",
                    "status": "planned",
                    "task": task,
                    "horizon": horizon,
                    "delay_ms": delay,
                    "scenes": "ID,OOD",
                    "method": "RTC",
                    "seeds": "fresh_block_to_be_frozen",
                })
    _write(output_dir / "delay_coverage_sweep_protocol.csv", sweep_rows,
           ["step", "status", "task", "horizon", "delay_ms", "scenes",
            "method", "seeds"])

    (output_dir / "FOLLOWUP_MANIFEST_README.md").write_text(
        """# CVPR follow-up protocol manifests

These CSVs are frozen planning artifacts, not completed results.
The first step (Stage 3 New queue/freshness analysis) can be run now
on the archived CSV. Steps 2--4 require a separate review of policy
compatibility, seed allocation, and compute budget before execution.
No row should be reported as evidence until its runner, checkpoint,
environment, and validated episode outputs are recorded.
"""
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build(args.output_dir)
    print(f"Wrote planning manifests to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
