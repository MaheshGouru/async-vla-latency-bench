#!/usr/bin/env python3
"""Generate the paper's Figures 1--5 and Table 1 from frozen result artifacts.

The script performs no outcome selection.  It reads the completed Exploratory OOD–Delay Screening/2/3
tables and the archived Held-Out Object-Layout Cross-Task Replication / Object-Layout Generalization / Multi-Stage Task Generalization analysis tables.
All outputs are written as both PNG and vector PDF where applicable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np


NAVY = "#17324D"
BLUE = "#2F6B9A"
CYAN = "#61A5C2"
ORANGE = "#E07A5F"
GOLD = "#E9C46A"
GREEN = "#4E937A"
RED = "#C44536"
PURPLE = "#6D597A"
LIGHT = "#F5F7FA"
GRID = "#D7DEE7"
TEXT = "#17212B"

TASK_LABELS = {
    "spatial_transport": "Single-stage transport",
    "goal_drawer": "Articulated/contact-rich",
    "long_stove_moka": "Multi-stage/sequential",
    "additional_multistage_task": "Second multi-stage task",
}
PERT_LABELS = {
    "object_layout": "Object layout",
    "robot_initial_state": "Robot initial state",
    "camera_viewpoint": "Camera viewpoint",
    "sensor_noise": "Sensor noise",
    "light_conditions": "Lighting",
    "background_textures": "Background texture",
    "language_instructions": "Language instruction",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def i(row: dict[str, str], key: str) -> int:
    return int(float(row[key]))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 11.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.edgecolor": NAVY,
            "axes.labelcolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
            "text.color": TEXT,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save(fig: plt.Figure, out: Path, stem: str) -> None:
    fig.savefig(out / f"{stem}.png", dpi=320, bbox_inches="tight")
    fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def rounded_box(ax, xy, width, height, text, fc, ec=NAVY, fontsize=9, lw=1.2):
    box = patches.FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
    )
    ax.add_patch(box)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=fontsize)
    return box


def arrow(ax, start, end, color=NAVY, connectionstyle="arc3"):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle="-|>", lw=1.35, color=color, connectionstyle=connectionstyle),
    )


def figure1(out: Path) -> None:
    fig = plt.figure(figsize=(11.8, 3.75))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1], wspace=0.10)
    ax = fig.add_subplot(gs[0, 0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("A  Asynchronous action generation and temporal coverage", loc="left", pad=4)

    rounded_box(ax, (0.03, 0.72), 0.17, 0.14, "Observation\n$o_t$", "#EAF2F8")
    rounded_box(ax, (0.28, 0.72), 0.22, 0.14, "VLA inference\n(measured latency)", "#E8F1EC")
    rounded_box(ax, (0.58, 0.72), 0.15, 0.14, "Added delay\n$d^*$", "#FBEDE8", ec=RED)
    rounded_box(ax, (0.81, 0.72), 0.16, 0.14, "Action chunk\n$a_{t:t+h-1}$", "#FFF4D6", ec="#A87500")
    arrow(ax, (0.20, 0.79), (0.28, 0.79))
    arrow(ax, (0.50, 0.79), (0.58, 0.79))
    arrow(ax, (0.73, 0.79), (0.81, 0.79))

    ax.text(0.03, 0.64, "Action queue", fontweight="bold", fontsize=10.5, va="center")
    x0, y0, cellw, cellh = 0.25, 0.51, 0.078, 0.105
    queue_labels = ["1", "2", "3", r"$\cdots$", r"$h-1$", r"$h$"]
    for k, label in enumerate(queue_labels):
        rect = patches.Rectangle((x0 + k * cellw, y0), cellw - 0.004, cellh, facecolor=GOLD, edgecolor=NAVY, lw=0.9)
        ax.add_patch(rect)
        ax.text(x0 + k * cellw + (cellw - 0.004) / 2, y0 + cellh / 2, label, ha="center", va="center", fontsize=8)
    coverage_end = x0 + len(queue_labels) * cellw - 0.004
    ax.plot([x0, coverage_end], [0.485, 0.485], color="#A87500", lw=1.2)
    ax.plot([x0, x0], [0.475, 0.495], color="#A87500", lw=1.2)
    ax.plot([coverage_end, coverage_end], [0.475, 0.495], color="#A87500", lw=1.2)
    ax.text((x0 + coverage_end) / 2, 0.455, "configured action coverage $h$", ha="center", va="top", fontsize=9)

    ax.text(0.03, 0.34, "Logical-time consequence", fontweight="bold", fontsize=10.5, va="center")
    ax.plot([0.25, 0.93], [0.28, 0.28], color=NAVY, lw=1.2)
    for x, label in [(0.25, "$o_t$ captured"), (0.54, "native\nresponse"), (0.72, "$d^*$\nresponse"), (0.93, "control time")]:
        ax.plot([x, x], [0.255, 0.305], color=NAVY, lw=1)
        ax.text(x, 0.19 if x < 0.9 else 0.32, label, ha="center", va="top" if x < 0.9 else "bottom", fontsize=8.3)
    ax.axvspan(0.54, 0.72, ymin=0.23, ymax=0.33, color=ORANGE, alpha=0.25)
    ax.text(0.63, 0.35, "added delay $d^*$", ha="center", color=RED, fontsize=8.5, fontweight="bold")
    ax.text(0.03, 0.045, "The queue executes while the next request is in flight; coverage must bridge measured latency + added delay.", fontsize=8.7)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")
    ax2.set_title("B  OOD × delay interaction", loc="left", pad=4)
    left, bottom, w, h = 0.18, 0.35, 0.33, 0.25
    colors = [["#EAF2F8", "#D9EAF3"], ["#FBEDE8", "#F6D2C8"]]
    labels = [["ID\nNative", "ID\n$d^*$"], ["OOD\nNative", "OOD\n$d^*$"]]
    for r in range(2):
        for c in range(2):
            rect = patches.Rectangle((left + c*w, bottom + (1-r)*h), w, h, facecolor=colors[r][c], edgecolor=NAVY, lw=1.2)
            ax2.add_patch(rect)
            ax2.text(left + c*w + w/2, bottom + (1-r)*h + h/2, labels[r][c], ha="center", va="center", fontweight="bold")
    ax2.text(left + w, 0.90, "Delay", ha="center", fontweight="bold")
    ax2.text(0.03, bottom + h, "Scene", rotation=90, va="center", fontweight="bold")
    ax2.text(0.50, 0.235, r"$I=[S_{OOD,d^*}-S_{OOD,N}]-[S_{ID,d^*}-S_{ID,N}]$", ha="center", fontsize=10)
    ax2.text(0.50, 0.145, "$I<0$: OOD reduces delay tolerance", ha="center", color=RED, fontweight="bold")
    ax2.text(0.50, 0.035, "All comparisons use paired initialization/seed blocks.", ha="center", fontsize=8.5)

    fig.subplots_adjust(left=0.025, right=0.99, top=0.94, bottom=0.025)
    save(fig, out, "figure1_experimental_concept")


def figure2(stage2_rows: list[dict[str, str]], out: Path) -> None:
    horizons = [10, 15, 20, 25, 30, 35]
    delays = [0, 100, 200, 300]
    pooled = defaultdict(lambda: [0, 0])
    for row in stage2_rows:
        key = (i(row, "configured_n_action_steps"), i(row, "added_delay_ms"))
        pooled[key][0] += int(float(row["success"]))
        pooled[key][1] += 1
    matrix = np.array([[pooled[(h, d)][0] / pooled[(h, d)][1] for d in delays] for h in horizons])

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.7, 4.15), gridspec_kw={"width_ratios": [1.03, 1.40], "wspace": 0.18})
    cmap = LinearSegmentedColormap.from_list("success", ["#B9403A", "#F4D06F", "#4E937A"])
    im = ax.imshow(matrix, vmin=0, vmax=1, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(delays)), ["Native", "+100", "+200", "+300"])
    ax.set_yticks(range(len(horizons)), horizons)
    ax.set_xlabel("Added delay (ms)")
    ax.set_ylabel("Configured action coverage $h$")
    ax.set_title("A  Pooled horizon × delay phase diagram")
    for r, h in enumerate(horizons):
        for c, d in enumerate(delays):
            successes, n = pooled[(h, d)]
            ax.text(c, r, f"{successes}/{n}", ha="center", va="center", color="white" if matrix[r,c] < .55 else TEXT, fontweight="bold")
    ax.add_patch(patches.Rectangle((-0.48, -0.48), 3.96, 0.96, fill=False, edgecolor=RED, lw=2.4))
    ax.text(3.34, -0.30, "$h=10$ collapse", color=RED, va="center", ha="right", fontsize=7.8, fontweight="bold")
    ax.add_patch(patches.Rectangle((-0.46, 1.53), 3.92, 2.92, fill=False, edgecolor=GREEN, lw=2.4))
    target_row = horizons.index(25)
    ax.add_patch(patches.Rectangle((1.54, target_row - 0.46), 0.92, 0.92,
                                   fill=False, edgecolor=NAVY, lw=2.2))
    ax.text(2.0, target_row - 0.53, "frozen operating point",
            ha="center", va="bottom", fontsize=8.2, color=NAVY)

    colors = {"goal_drawer": BLUE, "long_stove_moka": ORANGE, "spatial_transport": GREEN}
    rng = np.random.RandomState(7)
    for task, color in colors.items():
        rows = [r for r in stage2_rows if r["task_key"] == task]
        x = np.array([float(r["coverage_ratio_total_mean"]) for r in rows])
        y = np.array([float(r["success"]) for r in rows]) + rng.uniform(-0.025, 0.025, len(rows))
        ax2.scatter(x, y, s=32, alpha=0.58, color=color, edgecolors="white", linewidths=0.45, label=TASK_LABELS[task])
    h10 = [r for r in stage2_rows if i(r, "configured_n_action_steps") == 10]
    ax2.scatter([float(r["coverage_ratio_total_mean"]) for r in h10],
                [float(r["success"]) for r in h10], marker="x", s=34, lw=1.2, color=RED, label="$h=10$")
    ax2.axvline(1.0, ls="--", lw=1.2, color=RED)
    ax2.text(1.015, 0.49, "total delay exceeds\nconfigured coverage", color=RED, fontsize=8.3)
    op = [r for r in stage2_rows if i(r, "configured_n_action_steps") == 25 and i(r, "added_delay_ms") == 200]
    ax2.scatter([np.mean([float(r["coverage_ratio_total_mean"]) for r in op])], [np.mean([float(r["success"]) for r in op])],
                marker="*", s=210, color=NAVY, edgecolors="white", linewidths=0.8, zorder=6, label="$h=25,+200$ pooled")
    ax2.set_xlim(0.25, 1.78)
    ax2.set_ylim(-0.08, 1.08)
    ax2.set_xlabel("Total logical delay / configured action coverage")
    ax2.set_ylabel("Episode success (jittered)")
    ax2.set_yticks([0, 1], ["Failure", "Success"])
    ax2.set_title("B  Normalized temporal coverage")
    ax2.grid(axis="x", color=GRID, lw=0.7)
    ax2.legend(frameon=False, fontsize=7.5, loc="lower center",
               bbox_to_anchor=(0.5, 0.10), ncol=2, columnspacing=1.1, handletextpad=0.5)
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.12, top=0.84)
    fig.suptitle("Horizon × delay operating envelope (5 seeds/task/cell)", fontsize=14, fontweight="bold", x=0.02, ha="left", y=0.985)
    save(fig, out, "figure2_stage2_operating_envelope")


def figure3(stage1_episode_rows: list[dict[str, str]], four_cell: list[dict[str, str]], out: Path) -> None:
    # De-duplicate only by run_id; shared ID episodes occur once in the source file.
    unique = {row["run_id"]: row for row in stage1_episode_rows}
    rows = list(unique.values())
    agg = {}
    for method in ("naive_async", "rtc"):
        for scene in ("id", "ood"):
            for delay in (0, 200):
                cell = [r for r in rows if r["execution_method"] == method
                        and r["scene_condition"] == scene and i(r, "added_delay_ms") == delay]
                agg[(method, scene, delay)] = sum(int(float(r["success"])) for r in cell) / len(cell)
    method_interactions = {
        method: (agg[(method,"ood",200)]-agg[(method,"ood",0)])
                -(agg[(method,"id",200)]-agg[(method,"id",0)])
        for method in ("naive_async", "rtc")
    }

    tasks = ["spatial_transport", "goal_drawer", "long_stove_moka"]
    perts = list(PERT_LABELS)
    rtc = {(r["task"], r["perturbation"]): float(r["interaction_I"]) for r in four_cell if r["method"] == "rtc"}
    matrix = np.array([[rtc[(t,p)] for p in perts] for t in tasks])

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.8, 4.8), gridspec_kw={"width_ratios": [1.0, 1.55]})
    x = np.array([0, 1])
    styles = [
        ("naive_async", "id", BLUE, "o", "-", "Naive async — ID"),
        ("naive_async", "ood", BLUE, "s", "--", "Naive async — OOD"),
        ("rtc", "id", GREEN, "o", "-", "RTC — ID"),
        ("rtc", "ood", GREEN, "s", "--", "RTC — OOD"),
    ]
    label_offsets = {
        ("naive_async", "id"): -0.045,
        ("naive_async", "ood"): 0.035,
        ("rtc", "id"): 0.035,
        ("rtc", "ood"): -0.045,
    }
    for method, scene, color, marker, linestyle, label in styles:
        values = [agg[(method, scene, d)] for d in (0, 200)]
        ax.plot(x, values, marker=marker, ms=6.5, lw=2.1, ls=linestyle, color=color, label=label)
        dy = label_offsets[(method, scene)]
        for j, value in enumerate(values):
            dx = 0.035 if j == 0 else -0.035
            ax.text(j + dx, value + dy, f"{value*100:.1f}%", color=color, ha="center",
                    va="center", fontsize=8.0, fontweight="bold")
    ax.set_xticks(x, ["Native", "+200 ms"])
    ax.set_ylim(0.16, 0.98)
    ax.set_ylabel("Success rate")
    ax.yaxis.set_major_formatter(lambda v, pos: f"{v*100:.0f}%")
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.legend(frameon=False, loc="center left", fontsize=8.1)
    ax.set_title("A  Method × scene comparison")
    ax.text(0.5, 0.205,
            f"OOD × delay $I$: naive {method_interactions['naive_async']*100:+.1f} pp; "
            f"RTC {method_interactions['rtc']*100:+.1f} pp",
            ha="center", fontsize=8.2, fontweight="bold", color=NAVY)

    cmap = LinearSegmentedColormap.from_list("interaction", [RED, "white", GREEN])
    im = ax2.imshow(matrix, cmap=cmap, vmin=-0.4, vmax=0.4, aspect="auto")
    ax2.set_xticks(range(len(perts)), [PERT_LABELS[p] for p in perts], rotation=38, ha="right")
    ax2.set_yticks(range(len(tasks)), [TASK_LABELS[t] for t in tasks])
    ax2.set_title("B  Localized RTC interactions (exploratory)")
    for r in range(len(tasks)):
        for c in range(len(perts)):
            val = matrix[r,c]
            ax2.text(c, r, f"{val:+.1f}", ha="center", va="center", fontsize=8.5, fontweight="bold",
                     color="white" if abs(val) >= .3 else TEXT)
    cbar = fig.colorbar(im, ax=ax2, fraction=0.035, pad=0.025)
    cbar.set_label("OOD × delay interaction $I$")
    fig.suptitle("Figure 3 | Broad OOD screen (Exploratory OOD–Delay Screening; exploratory, 5 seeds/cell)", fontsize=14, fontweight="bold", x=0.06, ha="left", y=1.02)
    save(fig, out, "figure3_stage1_broad_ood_screen")


def figure3b(stage1_episode_rows: list[dict[str, str]], out: Path) -> None:
    """Show RTC-vs-naive performance with literal Stage-1 manifest identifiers."""
    rows = list({row["run_id"]: row for row in stage1_episode_rows}.values())
    tasks = ["spatial_transport", "goal_drawer", "long_stove_moka"]
    conditions = [
        "id", "object_layout", "robot_initial_state", "camera_viewpoint",
        "sensor_noise", "light_conditions", "background_textures",
        "language_instructions",
    ]
    cmap = LinearSegmentedColormap.from_list("method_delta", [RED, "white", GREEN])
    fig, axes = plt.subplots(1, 2, figsize=(15.2, 5.0), sharey=True,
                             gridspec_kw={"wspace": 0.08})
    fig.subplots_adjust(left=0.12, right=0.91, bottom=0.31, top=0.80)
    images = []
    for ax, delay, delay_label in zip(axes, (0, 200), ("Native", "+200 ms")):
        delta = np.zeros((len(tasks), len(conditions)))
        annotations: list[list[str]] = [["" for _ in conditions] for _ in tasks]
        for ti, task in enumerate(tasks):
            for ci, condition in enumerate(conditions):
                scene = "id" if condition == "id" else "ood"
                cell = [r for r in rows if r["task_key"] == task
                        and r["perturbation_key"] == condition
                        and r["scene_condition"] == scene
                        and i(r, "added_delay_ms") == delay]
                method_rows = {
                    method: [r for r in cell if r["execution_method"] == method]
                    for method in ("naive_async", "rtc")
                }
                if not all(method_rows.values()):
                    raise RuntimeError(f"missing Stage-1 cell: {task}/{condition}/d={delay}")
                successes = {
                    method: sum(int(float(r["success"])) for r in rs)
                    for method, rs in method_rows.items()
                }
                rates = {method: successes[method] / len(method_rows[method]) for method in method_rows}
                delta[ti, ci] = rates["rtc"] - rates["naive_async"]
                annotations[ti][ci] = (
                    f"{delta[ti,ci]*100:+.0f} pp\n"
                    f"R {successes['rtc']}/{len(method_rows['rtc'])} · N {successes['naive_async']}/{len(method_rows['naive_async'])}"
                )
        image = ax.imshow(delta, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
        images.append(image)
        ax.set_title(delay_label)
        ax.set_xticks(range(len(conditions)), conditions, rotation=34, ha="right", fontsize=8.2)
        ax.set_yticks(range(len(tasks)), tasks)
        for ti in range(len(tasks)):
            for ci in range(len(conditions)):
                ax.text(ci, ti, annotations[ti][ci], ha="center", va="center",
                        fontsize=6.6, fontweight="bold",
                        color="white" if abs(delta[ti,ci]) >= 0.55 else TEXT)
        ax.set_xlabel("exact perturbation_key")
    axes[0].set_ylabel("exact task_key")
    cbar = fig.colorbar(images[0], ax=axes, fraction=0.018, pad=0.018)
    cbar.set_label("RTC − naive async success rate")
    fig.suptitle(
        "Figure 3B | Stage-1 RTC advantage by exact task and perturbation identifiers",
        fontsize=14, fontweight="bold", x=0.055, ha="left", y=1.02,
    )
    fig.text(0.12, 0.035,
             "Cell text: percentage-point difference; R = RTC successes, N = naive-async successes (5 seeds per method/cell).",
             fontsize=8.5)
    save(fig, out, "figure3b_stage1_exact_task_condition_method_comparison")


def figure4(rows: list[dict[str, str]], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    configs = [
        ("spatial_transport", BLUE, "o"),
        ("goal_drawer", GREEN, "s"),
        ("long_stove_moka", ORANGE, "D"),
    ]
    offsets = {"spatial_transport": -0.35, "goal_drawer": 0, "long_stove_moka": 0.35}
    for task, color, marker in configs:
        rs = sorted([r for r in rows if r["task_key"] == task], key=lambda r: i(r,"configured_n_action_steps"))
        x = np.array([i(r,"configured_n_action_steps") for r in rs], dtype=float) + offsets[task]
        y = np.array([f(r,"interaction_I_h") for r in rs])
        lo = np.array([f(r,"paired_bootstrap95_low") for r in rs])
        hi = np.array([f(r,"paired_bootstrap95_high") for r in rs])
        ax.errorbar(x, y, yerr=[y-lo, hi-y], color=color, marker=marker, ms=7, lw=2, capsize=4,
                    label=TASK_LABELS[task])
    ax.axhline(0, color=NAVY, lw=1.1)
    ax.axvline(25, color=GRID, lw=8, alpha=.45, zorder=0)
    ax.text(25, 0.54, "frozen $h=25$", ha="center", color=NAVY, fontsize=8.5)
    ax.set_xticks([20,25,30])
    ax.set_xlabel("Configured action coverage $h$")
    ax.set_ylabel("OOD × delay interaction $I$")
    ax.set_ylim(-0.78, 0.62)
    ax.grid(axis="y", color=GRID, lw=.7)
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5,-0.27))
    ax.set_title("Object-layout interaction across held-out tasks and horizons")
    ax.text(0.01, 0.02, "Points: paired estimates; bars: paired-seed bootstrap 95% CIs (8 held-out seeds).",
            transform=ax.transAxes, fontsize=8.5)
    fig.suptitle("Held-out and cross-task replication", fontsize=14, fontweight="bold", x=0.06, ha="left", y=1.02)
    save(fig, out, "figure4_stage3_stage3b_replication")


def figure5(
    a_rows: list[dict[str, str]],
    b_rows: list[dict[str, str]],
    out: Path,
    *,
    compact: bool = False,
) -> None:
    records = []
    layout_labels = {
        "1950": "Level 3, sample 1  (c1950)",
        "1953": "Level 4, sample 2  (c1953)",
        "1955": "Level 4, sample 4  (c1955)",
        "2064": "+ antihistamine, veg. juice, ink  (c2064)",
        "2066": "+ canned food, ink, antihistamine  (c2066)",
        "2074": "+ aspirin, 2× baby oil, sardines, veg. juice  (c2074)",
    }
    if compact:
        layout_labels.update(
            {
                "1950": "Level 3, sample 1\n(c1950)",
                "1953": "Level 4, sample 2\n(c1953)",
                "1955": "Level 4, sample 4\n(c1955)",
                "2064": "+ antihistamine, veg. juice,\nink (c2064)",
                "2066": "+ canned food, ink,\nantihistamine (c2066)",
                "2074": "+ aspirin, 2× baby oil,\nsardines, veg. juice (c2074)",
            }
        )
    for group, rows in [("Long stove–moka task",a_rows),("Second multi-stage task",b_rows)]:
        for row in rows:
            records.append((group, layout_labels[row["classification_id"]], f(row,"interaction_I_variant"),
                            f(row,"paired_bootstrap95_low"), f(row,"paired_bootstrap95_high")))
    y = np.arange(len(records))[::-1]
    # The compact layout is sized for a paper's full text width.  It removes the
    # redundant section-level heading while keeping type near the original size.
    fig, ax = plt.subplots(figsize=(7.5, 3.75) if compact else (9.2, 5.1))
    ax.axhspan(2.5, 5.5, color="#F2F6FA", zorder=0)
    ax.axhspan(-0.5, 2.5, color="#FBF3ED", zorder=0)
    for yy, (group,label,val,lo,hi) in zip(y,records):
        color = BLUE if group.startswith("Long") else ORANGE
        ax.errorbar(val, yy, xerr=[[val-lo],[hi-val]], fmt="o", ms=8, color=color, ecolor=color, capsize=4, lw=2)
        ax.text(1.18, yy, f"{val:+.3f}  [{lo:+.3f}, {hi:+.3f}]", va="center", fontsize=8.4, family="monospace")
    ax.axvline(0, color=NAVY, lw=1.15)
    ax.set_yticks(y, [r[1] for r in records])
    ax.set_xlim(-1.0, 1.62)
    ax.set_xlabel("OOD × delay interaction $I$  (paired-bootstrap 95% CI)")
    ax.grid(axis="x", color=GRID, lw=.7)
    ax.text(-0.98, 5.25, "Long stove–moka", color=BLUE, fontweight="bold")
    ax.text(-0.98, 2.25, "Second multi-stage task", color=ORANGE, fontweight="bold")
    ax.text(-0.98, -0.38, "$I<0$: OOD layout reduces delay tolerance", color=RED, fontsize=8.5)
    ax.text(0.35, -0.38, "$I>0$: delay is less damaging under OOD", color=GREEN, fontsize=8.5)
    ax.set_title(
        "Per-layout generalization is heterogeneous within and across tasks",
        pad=7 if compact else None,
    )
    if not compact:
        fig.suptitle("Layout-variant and task generalization", fontsize=14, fontweight="bold", x=0.06, ha="left", y=1.02)
    save(
        fig,
        out,
        "figure5_experiments_a_b_layout_generalization_compact"
        if compact
        else "figure5_experiments_a_b_layout_generalization",
    )


def table1(out: Path) -> None:
    headers = ["Stage", "Design role", "Evidence", "Claim disposition"]
    rows = [
        ["Exploratory OOD–Delay Screening", "Broad exploratory screen", "480 episodes; 7 OOD families", "No broad OOD amplification; localized candidates"],
        ["Confirmatory Horizon–Delay Operating Envelope", "Operating-envelope sensitivity", "6 horizons × 4 delays × 3 tasks", "$h=10$ collapses; $h=20$–30 locally stable"],
        ["Held-Out OOD–Delay Horizon Confirmation", "Held-out confirmation", "8 new seeds; frozen horizons", "Most candidates do not replicate; long × layout survives"],
        ["Held-Out Object-Layout Cross-Task Replication", "Cross-task object-layout replication", "3 tasks across $h=20,25,30$", "Effect is task-dependent, not family-wide"],
        ["Object-Layout Generalization", "Within-task layout generalization", "3 new long-task layouts", "Negative in 2/3; heterogeneous across layouts"],
        ["Multi-Stage Task Generalization", "Second-task generalization", "3 layouts on new multi-stage task", "Negative in 1/3; no general multi-stage vulnerability"],
        ["Initialization-State Audit", "Initialization audit", "Reset-only, failed closed", "One distinct OOD reset/variant; no initialization claim"],
    ]
    with (out / "table1_experiment_progression.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(14.6, 4.6))
    ax.axis("off")
    table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="left", colLoc="left",
                     colWidths=[.10,.23,.25,.42])
    table.auto_set_font_size(False)
    table.set_fontsize(8.15)
    table.scale(1, 1.75)
    for (r,c), cell in table.get_celld().items():
        cell.set_edgecolor("white")
        cell.set_linewidth(1.3)
        if r == 0:
            cell.set_facecolor(NAVY)
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#F2F6FA" if r % 2 else "#FAFBFC")
            if c == 0:
                cell.get_text().set_fontweight("bold")
                cell.get_text().set_color(BLUE if r < 5 else PURPLE)
    ax.set_title("Table 1 | Experiment progression and claim disposition", fontsize=14, fontweight="bold", loc="left", pad=14)
    ax.text(0, -0.03, "Initialization-State Audit is a documented design limitation, not a policy-outcome experiment.", transform=ax.transAxes, fontsize=8.5)
    save(fig, out, "table1_experiment_progression")


def write_sources(paths: dict[str, Path], out: Path) -> None:
    with (out / "figure_source_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["figure", "source_file", "sha256"])
        mapping = {
            "Figure 2": ["stage2_episodes"],
            "Figure 3": ["stage1_episodes", "stage1_four_cell"],
            "Figure 3B": ["stage1_episodes"],
            "Figure 4": ["stage3b_interactions"],
            "Figure 5": ["experiment_a_interactions", "experiment_b_interactions"],
        }
        for figure, keys in mapping.items():
            for key in keys:
                writer.writerow([figure, str(paths[key].resolve()), sha256(paths[key])])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "generated")
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    workspace = repo.parent
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "stage1_episodes": workspace / "stage1/stage1_episode_results.csv",
        "stage1_four_cell": workspace / "stage1/analysis/stage1_table_four_cell.csv",
        "stage2_episodes": workspace / "stage2/stage2_local_sensitivity_episode_results.csv",
        "stage3b_interactions": repo / "paper_figures/source/stage3b/analysis/stage3b_interaction_by_task_horizon.csv",
        "experiment_a_interactions": repo / "paper_figures/source/experiment_a/analysis/experiment_a_interaction_by_variant.csv",
        "experiment_b_interactions": repo / "paper_figures/source/experiment_b/analysis/experiment_b_interaction_by_variant.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing required source files:\n" + "\n".join(missing))
    style()
    figure1(out)
    figure2(read_csv(paths["stage2_episodes"]), out)
    figure3(read_csv(paths["stage1_episodes"]), read_csv(paths["stage1_four_cell"]), out)
    figure3b(read_csv(paths["stage1_episodes"]), out)
    figure4(read_csv(paths["stage3b_interactions"]), out)
    experiment_a = read_csv(paths["experiment_a_interactions"])
    experiment_b = read_csv(paths["experiment_b_interactions"])
    figure5(experiment_a, experiment_b, out)
    figure5(experiment_a, experiment_b, out, compact=True)
    table1(out)
    write_sources(paths, out)
    print(f"PASS: generated Figures 1--5, supplemental Figure 3B, and Table 1 in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
