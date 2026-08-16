#!/usr/bin/env python3
"""Generate the frozen Stage 2 tables, figures, and observations."""

import argparse
import math
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage2 import ADDED_DELAYS_MS, HORIZONS


def rate(rows):
    return sum(int(r["success"]) for r in rows) / len(rows) if rows else float("nan")


def mean(rows, field):
    values = [float(r[field]) for r in rows if r.get(field, "") not in ("", "nan")]
    return sum(values) / len(values) if values else float("nan")


def wilson(successes, trials, z=1.959963984540054):
    if not trials:
        return float("nan"), float("nan")
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials) / denom
    return center - margin, center + margin


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    rows = [r for r in read_csv(args.results) if r.get("status", "").startswith("ok")]
    if len(rows) != 360 and not args.allow_incomplete:
        raise ValueError(f"refusing incomplete analysis: {len(rows)}/360")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tasks = sorted({r["task_key"] for r in rows})
    summary = []
    for task in tasks:
        for horizon in HORIZONS:
            for delay in ADDED_DELAYS_MS:
                cell = [r for r in rows if r["task_key"] == task and int(r["configured_n_action_steps"]) == horizon and int(r["added_delay_ms"]) == delay]
                successes = sum(int(r["success"]) for r in cell)
                ci_low, ci_high = wilson(successes, len(cell))
                summary.append({
                    "task_key": task, "configured_n_action_steps": horizon,
                    "added_delay_ms": delay, "completed": len(cell), "successes": successes,
                    "success_rate": rate(cell), "success_wilson95_low": ci_low,
                    "success_wilson95_high": ci_high,
                    "mean_request_latency_ms": mean(cell, "request_latency_mean_ms"),
                    "mean_total_delay_steps": mean(cell, "logical_delay_steps_mean"),
                    "mean_coverage_ratio_total": mean(cell, "coverage_ratio_total_mean"),
                    "mean_frozen_prefix_steps": mean(cell, "rtc_mean_frozen_prefix_steps"),
                    "mean_guided_overlap_steps": mean(cell, "rtc_mean_guided_overlap_steps"),
                    "mean_fresh_suffix_steps": mean(cell, "rtc_mean_fresh_suffix_steps"),
                })
    write_csv(args.output_dir / "stage2_local_sensitivity_summary.csv", summary)
    neighborhood = [r for r in summary if int(r["configured_n_action_steps"]) in (20, 25, 30)]
    write_csv(args.output_dir / "stage2_local_neighborhood.csv", neighborhood)
    native = [r for r in summary if int(r["added_delay_ms"]) == 0]
    write_csv(args.output_dir / "stage2_native_baseline_by_horizon.csv", native)
    drops = []
    for task in tasks:
        for horizon in HORIZONS:
            baseline = next(r for r in summary if r["task_key"] == task and int(r["configured_n_action_steps"]) == horizon and int(r["added_delay_ms"]) == 0)
            for delay in (100, 200, 300):
                shifted = next(r for r in summary if r["task_key"] == task and int(r["configured_n_action_steps"]) == horizon and int(r["added_delay_ms"]) == delay)
                drops.append({"task_key": task, "configured_n_action_steps": horizon, "added_delay_ms": delay,
                    "native_success_rate": baseline["success_rate"], "delayed_success_rate": shifted["success_rate"],
                    "delta_from_native": float(shifted["success_rate"]) - float(baseline["success_rate"])})
    write_csv(args.output_dir / "stage2_delay_drop_from_native.csv", drops)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    labels = {"spatial_transport": "spatial", "goal_drawer": "goal", "long_stove_moka": "long"}
    for task in tasks:
        matrix = np.array([[float(next(r["success_rate"] for r in summary if r["task_key"] == task and int(r["configured_n_action_steps"]) == h and int(r["added_delay_ms"]) == d)) for d in ADDED_DELAYS_MS] for h in HORIZONS])
        fig, ax = plt.subplots(figsize=(6, 5)); image = ax.imshow(matrix, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax.set_xticks(range(4), ["Native", "+100", "+200", "+300"]); ax.set_yticks(range(6), HORIZONS)
        ax.set_xlabel("Added delay (ms)"); ax.set_ylabel("Configured action coverage"); ax.set_title(task)
        for i in range(6):
            for j in range(4): ax.text(j, i, f"{matrix[i,j]:.1f}", ha="center", va="center", color="white" if matrix[i,j] < .6 else "black")
        fig.colorbar(image, ax=ax, label="Success rate"); fig.tight_layout()
        fig.savefig(args.output_dir / f"stage2_local_surface_{labels[task]}.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    for task in tasks:
        values = [float(next(r["success_rate"] for r in summary if r["task_key"] == task and int(r["configured_n_action_steps"]) == h and int(r["added_delay_ms"]) == 200)) for h in HORIZONS]
        ax.plot(HORIZONS, values, marker="o", label=task)
    ax.axvline(25, color="black", linestyle="--", alpha=.5); ax.set(xlabel="Configured action coverage", ylabel="Success rate", ylim=(-.05, 1.05), title="Stage 2 horizon slice at +200 ms"); ax.legend(); fig.tight_layout(); fig.savefig(args.output_dir / "stage2_horizon_slice_200ms.png", dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 5))
    for task in tasks:
        values = [float(next(r["success_rate"] for r in summary if r["task_key"] == task and int(r["configured_n_action_steps"]) == 25 and int(r["added_delay_ms"]) == d)) for d in ADDED_DELAYS_MS]
        ax.plot(ADDED_DELAYS_MS, values, marker="o", label=task)
    ax.axvline(200, color="black", linestyle="--", alpha=.5); ax.set(xlabel="Added delay (ms)", ylabel="Success rate", ylim=(-.05, 1.05), title="Stage 2 delay slice at 25 actions"); ax.legend(); fig.tight_layout(); fig.savefig(args.output_dir / "stage2_delay_slice_25actions.png", dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 5))
    for task in tasks:
        subset = [r for r in rows if r["task_key"] == task]
        ax.scatter([float(r["coverage_ratio_total_mean"]) for r in subset], [int(r["success"]) for r in subset], alpha=.35, label=task)
    ax.set(xlabel="Total logical delay steps / configured action coverage", ylabel="Episode success", title="Descriptive normalized coverage"); ax.legend(); fig.tight_layout(); fig.savefig(args.output_dir / "stage2_normalized_coverage.png", dpi=180); plt.close(fig)

    local_rates = [float(r["success_rate"]) for r in neighborhood]
    spread = max(local_rates) - min(local_rates) if local_rates else float("nan")
    observations = args.output_dir / "STAGE_2_LOCAL_SENSITIVITY_OBSERVATIONS.md"
    observations.write_text(
        "# Stage 2 Local Sensitivity Observations\n\n"
        f"- Completed: {len(rows)}/360 episodes.\n"
        f"- Maximum success-rate spread across the pooled 20/25/30 neighborhood cells: {spread:.3f}.\n\n"
        "## Decision\n\nClassification as locally stable, locally sensitive, or potentially under-covered requires task-level review of the generated surfaces, Native-normalized drops, and latency diagnostics; it is intentionally not assigned by an arbitrary scalar threshold. Stage 1 remains frozen at 25/+200 regardless of this result.\n"
    )
    print(f"PASS: complete Stage 2 analysis generated in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
