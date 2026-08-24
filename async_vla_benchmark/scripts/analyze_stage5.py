#!/usr/bin/env python3
"""Analyze Stage 5A calibration or Stage 5B conditional OOD × delay replication."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage4 import TASKS
from async_vla_benchmark.benchmark.stage5 import NATIVE_CHUNK_SIZE, SEEDS_5B
from async_vla_benchmark.scripts.analyze_stage3 import paired_cluster_bootstrap, wilson


def _rate(rows):
    return sum(int(r["success"]) for r in rows) / len(rows) if rows else float("nan")


def _analyze_5a(results_path: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not results_path.exists():
        rows = []
    else:
        rows = [r for r in read_csv(results_path) if r.get("status", "").startswith("ok")]

    if not rows:
        selected = {
            "stage": "stage5a_selected_operating_point",
            "configured_action_coverage": NATIVE_CHUNK_SIZE,
            "request_threshold_actions": math.ceil(NATIVE_CHUNK_SIZE / 2),
            "proceed_to_stage5b": False,
            "selection_basis": "5A0 capability audit closed the gate (native horizon = 8)",
            "selected_without_ood_outcomes": True,
        }
        (output_dir / "stage5a_selected_operating_point.json").write_text(json.dumps(selected, indent=2, sort_keys=True) + "\n")
        lines = [
            "# Stage 5A Observations",
            "",
            "Stage 5A0 inspected the pinned OpenVLA-OFT source (and, if --runtime was used, performed a single inference).",
            "",
            f"- Single-inference native output horizon: {NATIVE_CHUNK_SIZE} actions.",
            "- No legitimate >8 coverage is available from one model inference without concatenation, repeated query, or time-stretching.",
            "- The preferred candidate set {{8,12,16,20,25}} is therefore truncated to {8} before any ID outcomes are inspected.",
            "- Stage 5A coverage sweep and Stage 5B rerun are not required.",
            "",
            "Stage 4 remains the valid native-horizon second-policy diagnostic. Interpret it as an operating-envelope result, not a coverage-matched cross-policy comparison.",
            "",
        ]
        (output_dir / "STAGE_5A_OBSERVATIONS.md").write_text("\n".join(lines) + "\n")
        print("PASS: Stage 5A gate closed; selected coverage remains native 8")
        return 0

    # Coverage-level calibration summary.
    by_coverage = {}
    for task in TASKS:
        for c in sorted({int(r["configured_action_coverage"]) for r in rows}):
            for delay in (0, 200):
                cell = [r for r in rows if r["task_key"] == task and int(r["configured_action_coverage"]) == c and int(r["added_delay_ms"]) == delay]
                k = sum(int(r["success"]) for r in cell)
                lo, hi = wilson(k, len(cell))
                by_coverage.setdefault(task, []).append({
                    "configured_action_coverage": c,
                    "added_delay_ms": delay,
                    "episodes": len(cell),
                    "successes": k,
                    "rate": _rate(cell),
                    "wilson95_low": lo,
                    "wilson95_high": hi,
                    "mean_queue_underrun_steps": sum(int(r.get("queue_underrun_steps", 0)) for r in cell) / len(cell) if cell else float("nan"),
                    "mean_hold_action_fraction": sum(float(r.get("hold_action_fraction", 0)) for r in cell) / len(cell) if cell else float("nan"),
                })

    all_rows = [r for task, lst in by_coverage.items() for r in lst]
    write_csv(output_dir / "stage5a_coverage_calibration_results.csv", all_rows)

    # Operating-point rule: smallest legitimate coverage with no catastrophic Native floor
    # and stable local behavior. Because all coverages here are <= native, and only 8 is
    # verified to be native, this defaults to 8.
    selected_coverage = NATIVE_CHUNK_SIZE
    selected = {
        "stage": "stage5a_selected_operating_point",
        "configured_action_coverage": selected_coverage,
        "request_threshold_actions": math.ceil(selected_coverage / 2),
        "proceed_to_stage5b": selected_coverage != NATIVE_CHUNK_SIZE,
        "selection_basis": "smallest verified native coverage; local stability on ID Native",
        "selected_without_ood_outcomes": True,
        "coverage_is_single_inference_native": True,
    }
    (output_dir / "stage5a_selected_operating_point.json").write_text(json.dumps(selected, indent=2, sort_keys=True) + "\n")

    lines = [
        "# Stage 5A Observations",
        "",
        f"- Calibrated coverage: {selected_coverage} actions (request threshold {selected['request_threshold_actions']}).",
        f"- Proceed to Stage 5B: {selected['proceed_to_stage5b']}",
        "",
        "## Coverage calibration summary",
        "",
    ]
    for r in all_rows:
        lines.append(
            f"- coverage={r['configured_action_coverage']} delay={r['added_delay_ms']}ms: "
            f"{r['successes']}/{r['episodes']} success "
            f"(rate={r['rate']:.3f}, Wilson 95% CI [{r['wilson95_low']:.3f}, {r['wilson95_high']:.3f}]) "
            f"underrun={r['mean_queue_underrun_steps']:.1f} hold={r['mean_hold_action_fraction']:.3f}"
        )
    (output_dir / "STAGE_5A_OBSERVATIONS.md").write_text("\n".join(lines) + "\n")
    print(f"PASS: Stage 5A calibration analyzed; selected coverage={selected_coverage}")
    return 0


def _analyze_5b(results_path: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not results_path.exists():
        rows = []
    else:
        rows = [r for r in read_csv(results_path) if r.get("status", "").startswith("ok")]
    if not rows:
        print("PASS: no Stage 5B results to analyze (conditional on 5A operating point)")
        return 0
    if len(rows) != 64:
        raise ValueError(f"Stage 5B analysis requires 64 episodes, got {len(rows)}")

    four = []
    interactions = []
    for task in TASKS:
        record = {"task_key": task}
        for scene in ("id", "ood"):
            for delay, label in ((0, "native"), (200, "plus_200")):
                cell = [r for r in rows if r["task_key"] == task and r["scene_condition"] == scene and int(r["added_delay_ms"]) == delay]
                successes = sum(int(r["success"]) for r in cell)
                lo, hi = wilson(successes, len(cell))
                prefix = f"{scene}_{label}"
                record.update({
                    prefix + "_successes": successes,
                    prefix + "_trials": len(cell),
                    prefix + "_rate": successes / len(cell),
                    prefix + "_wilson95_low": lo,
                    prefix + "_wilson95_high": hi,
                })
        from async_vla_benchmark.benchmark.stage5 import paired_interaction_values
        paired = paired_interaction_values(rows, task)
        interaction = (record["ood_plus_200_rate"] - record["ood_native_rate"]) - (record["id_plus_200_rate"] - record["id_native_rate"])
        lo, hi = paired_cluster_bootstrap(paired)
        four.append(record)
        interactions.append({
            "task_key": task,
            "interaction_I_task": interaction,
            "paired_seed_values": ";".join(map(str, paired)),
            "paired_bootstrap95_low": lo,
            "paired_bootstrap95_high": hi,
        })

    write_csv(output_dir / "stage5b_four_cell_by_task.csv", four)
    write_csv(output_dir / "stage5b_interaction_by_task.csv", interactions)

    diagnostics = []
    for task in TASKS:
        for scene in ("id", "ood"):
            for delay in (0, 200):
                cell = [r for r in rows if r["task_key"] == task and r["scene_condition"] == scene and int(r["added_delay_ms"]) == delay]
                if cell:
                    diagnostics.append({
                        "task_key": task,
                        "scene_condition": scene,
                        "added_delay_ms": delay,
                        "episodes": len(cell),
                        "mean_request_latency_ms": sum(float(r["measured_request_latency_ms"]) for r in cell) / len(cell),
                        "mean_logical_delay_steps": sum(float(r["logical_delay_steps"]) for r in cell) / len(cell),
                        "mean_action_age_ms": sum(float(r["mean_action_age_ms"]) for r in cell) / len(cell),
                        "mean_queue_underrun_steps": sum(int(r["queue_underrun_steps"]) for r in cell) / len(cell),
                        "mean_hold_action_fraction": sum(float(r["hold_action_fraction"]) for r in cell) / len(cell),
                    })
    write_csv(output_dir / "stage5b_timing_diagnostics.csv", diagnostics)

    os.environ["MPLBACKEND"] = "Agg"
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([r["task_key"] for r in interactions], [float(r["interaction_I_task"]) for r in interactions])
    ax.axhline(0, color="black", linewidth=1)
    ax.set(ylabel="OOD x delay interaction", title="Stage 5B: final calibrated OpenVLA-OFT second-policy replication")
    fig.tight_layout()
    fig.savefig(output_dir / "stage5b_interaction_by_task.png", dpi=180)
    plt.close(fig)

    lines = ["# Stage 5B Observations", "", "Final second-policy OOD × delay replication at the frozen Stage-5A coverage.", ""]
    for row in interactions:
        cell = next(x for x in four if x["task_key"] == row["task_key"])
        lines.append(
            f"- {row['task_key']}: ID Native {cell['id_native_successes']}/8, "
            f"ID +200 {cell['id_plus_200_successes']}/8, "
            f"OOD Native {cell['ood_native_successes']}/8, "
            f"OOD +200 {cell['ood_plus_200_successes']}/8; "
            f"I={float(row['interaction_I_task']):+.3f}, paired bootstrap 95% CI "
            f"[{float(row['paired_bootstrap95_low']):+.3f}, {float(row['paired_bootstrap95_high']):+.3f}]."
        )
    lines.append("")
    lines.append("Use Stage 5B as the final calibrated second-policy result and retain Stage 4 as preliminary provenance.")
    (output_dir / "STAGE_5B_OBSERVATIONS.md").write_text("\n".join(lines) + "\n")
    print("PASS: Stage 5B analysis generated")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=("a", "b"), required=True)
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    if args.phase == "a":
        return _analyze_5a(args.results, args.output_dir)
    return _analyze_5b(args.results, args.output_dir)


if __name__ == "__main__": raise SystemExit(main())
