#!/usr/bin/env python3
"""Generate all required Stage 1 figures from validated CSV artifacts."""

import argparse
import os
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.stage1 import PERTURBATIONS, TASK_GROUP_LABELS


def main() -> int:
    os.environ["MPLBACKEND"] = "Agg"
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--tables-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    import matplotlib.pyplot as plt
    import numpy as np
    args.output_dir.mkdir(parents=True, exist_ok=True)
    four = read_csv(args.tables_dir / "stage1_table_four_cell.csv")
    perturb = read_csv(args.tables_dir / "stage1_table_perturbation_summary.csv")
    mechanisms = read_csv(args.tables_dir / "stage1_table_mechanism_summary.csv")
    tasks = read_csv(args.tables_dir / "stage1_table_task_group_summary.csv")
    results = read_csv(args.results)
    task_keys = sorted({r["task"] for r in four})
    perturb_keys = [p.key for p in PERTURBATIONS]

    for method, filename in (("naive_async", "stage1_heatmap_naive.png"), ("rtc", "stage1_heatmap_rtc.png")):
        matrix = np.array([[float(next(r["interaction_I"] for r in four if r["task"] == task and r["perturbation"] == p and r["method"] == method)) for p in perturb_keys] for task in task_keys])
        fig, ax = plt.subplots(figsize=(11, 4)); image = ax.imshow(matrix, vmin=-1, vmax=1, cmap="coolwarm")
        ax.set_xticks(range(7), [p.label for p in PERTURBATIONS], rotation=35, ha="right"); ax.set_yticks(range(3), task_keys)
        for i in range(3):
            for j in range(7): ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center")
        fig.colorbar(image, ax=ax, label="OOD × delay interaction I"); fig.tight_layout(); fig.savefig(args.output_dir / filename, dpi=180); plt.close(fig)

    fig, axes = plt.subplots(3, 2, figsize=(12, 11), sharex=True, sharey=True)
    for ax, (task, method) in zip(axes.flat, [(t, m) for t in task_keys for m in ("naive_async", "rtc")]):
        subset = [r for r in four if r["task"] == task and r["method"] == method]
        for row in subset:
            color = ax._get_lines.get_next_color()
            ax.plot([0,1], [float(row["id_low"]), float(row["id_high"])], color=color, alpha=.35, linestyle="--")
            ax.plot([0,1], [float(row["ood_low"]), float(row["ood_high"])], color=color, alpha=.75, label=row["perturbation"])
        ax.set_title(f"{task} / {method}"); ax.set_xticks([0,1], ["Native", "Native + d*"]); ax.set_ylim(-.05,1.05)
    fig.tight_layout(); fig.savefig(args.output_dir / "stage1_interaction_four_cell.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10,5))
    for method, marker in (("naive_async", "o"), ("rtc", "s")):
        subset = [r for r in perturb if r["method"] == method]; ax.plot(range(7), [float(r["pooled_I"]) for r in subset], marker=marker, label=method)
    ax.axhline(0,color="black",lw=1); ax.set_xticks(range(7), [p.label for p in PERTURBATIONS], rotation=35,ha="right"); ax.legend(); fig.tight_layout(); fig.savefig(args.output_dir / "stage1_perturbation_ranking.png",dpi=180); plt.close(fig)

    def grouped(rows, group_key, value_key, filename):
        labels=sorted({r[group_key] for r in rows}); fig,ax=plt.subplots(figsize=(9,5)); x=np.arange(len(labels)); width=.35
        for offset,method in ((-.5,"naive_async"),(.5,"rtc")):
            values=[float(next(r[value_key] for r in rows if r[group_key]==label and r["method"]==method)) for label in labels]
            ax.bar(x+offset*width,values,width,label=method)
        ax.axhline(0,color="black",lw=1); ax.set_xticks(x,labels,rotation=25,ha="right"); ax.legend(); fig.tight_layout(); fig.savefig(args.output_dir/filename,dpi=180); plt.close(fig)
    grouped(mechanisms,"mechanism_group","mean_I","stage1_mechanism_summary.png")
    grouped(tasks,"task","mean_I","stage1_task_group_summary.png")

    fig,ax=plt.subplots(figsize=(9,5)); valid=[r for r in results if r.get("action_age_p95_ms") not in ("","nan")]
    ax.scatter([float(r["action_age_p95_ms"]) for r in valid],[int(r["success"]) for r in valid],alpha=.35); ax.set_xlabel("p95 action age (ms)"); ax.set_ylabel("success"); fig.tight_layout(); fig.savefig(args.output_dir/"stage1_action_age_outcome.png",dpi=180); plt.close(fig)
    print(f"wrote required Stage 1 figures to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
