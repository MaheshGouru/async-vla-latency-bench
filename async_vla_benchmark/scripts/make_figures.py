#!/usr/bin/env python3
"""Generate aggregate figures from validated benchmark summaries."""

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np


def _bootstrap_ci(values, n_boot=1000, ci=0.95):
    if not values:
        return float("nan"), float("nan")
    boot_means = []
    for _ in range(n_boot):
        sample = [random.choice(values) for _ in values]
        boot_means.append(float(np.mean(sample)))
    lower = (1 - ci) / 2
    upper = 1 - lower
    return float(np.percentile(boot_means, lower * 100)), float(np.percentile(boot_means, upper * 100))


def _load_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _group(summaries, x_key, y_key, group_key):
    groups = {}
    for s in summaries:
        g = s.get(group_key, "unknown")
        groups.setdefault(g, {"x": [], "y": []})
        groups[g]["x"].append(s.get(x_key))
        groups[g]["y"].append(s.get(y_key))
    return groups


def _plot_lines(ax, summaries, x_key, y_key, group_key, label):
    groups = _group(summaries, x_key, y_key, group_key)
    for name, data in sorted(groups.items()):
        pairs = sorted({x: [] for x in data["x"]}.items())
        # Recompute per x
        x_vals = sorted(set(data["x"]))
        means, lowers, uppers = [], [], []
        for xv in x_vals:
            vals = [y for x, y in zip(data["x"], data["y"]) if x == xv and not math.isnan(y)]
            if vals:
                lo, hi = _bootstrap_ci(vals)
                means.append(np.mean(vals))
                lowers.append(lo)
                uppers.append(hi)
            else:
                means.append(float("nan"))
                lowers.append(float("nan"))
                uppers.append(float("nan"))
        ax.plot(x_vals, means, marker="o", label=f"{name}")
        ax.fill_between(x_vals, lowers, uppers, alpha=0.2)
    ax.set_xlabel(x_key)
    ax.set_ylabel(y_key)
    ax.set_title(label)
    ax.legend()


def main():
    import math  # noqa: F811

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required to generate figures") from exc

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    summaries_dir = args.output_dir / "summaries"
    figures_dir = args.output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    core = _load_json(summaries_dir / "core_summaries.json")
    horizon = _load_json(summaries_dir / "horizon_sweep_summaries.json")

    # Convert latency profile names to numeric added latency for plotting.
    profile_order = {"ideal": 1, "native": 2, "native_plus_300": 3, "native_plus_700": 4}

    def numeric_profile(s):
        name = s.get("latency_profile", "native")
        mapping = {"ideal": 0, "native": 0, "native_plus_300": 300, "native_plus_700": 700}
        return mapping.get(name, 0)

    def profile_x(s):
        return s.get("action_age_ms", numeric_profile(s))

    for filename, x_key, y_key, group_key, title in [
        ("success_vs_delay.png", "action_age_ms", "success", "strategy", "Success vs action age"),
        ("action_age_vs_delay.png", "latency_profile", "mean_action_age_ms", "strategy", "Mean action age vs latency profile"),
        ("queue_underruns_vs_delay.png", "latency_profile", "queue_underrun_steps", "strategy", "Queue underruns vs latency profile"),
        ("completion_time_vs_delay.png", "latency_profile", "logical_completion_time_seconds", "strategy", "Completion time vs latency profile"),
        ("action_jerk_vs_delay.png", "latency_profile", "mean_action_jerk_l2", "strategy", "Action jerk vs latency profile"),
    ]:
        fig, ax = plt.subplots(figsize=(8, 5))
        _plot_lines(ax, core, x_key, y_key, group_key, title)
        fig.savefig(figures_dir / filename, dpi=150)
        plt.close(fig)

    if horizon:
        fig, ax = plt.subplots(figsize=(8, 5))
        _plot_lines(ax, horizon, "fixed_horizon", "success", "strategy", "Horizon success trade-off")
        fig.savefig(figures_dir / "horizon_success_tradeoff.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 5))
        _plot_lines(ax, horizon, "fixed_horizon", "mean_action_age_ms", "strategy", "Horizon action age trade-off")
        fig.savefig(figures_dir / "horizon_action_age_tradeoff.png", dpi=150)
        plt.close(fig)

    print(f"wrote figures to {figures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
