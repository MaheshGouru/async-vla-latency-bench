#!/usr/bin/env python3
"""Analyze temporal coverage and queue mechanisms in Stage 3 New.

This is a descriptive, CPU-only post-processing script.  It consumes the
episode-level CSV emitted by ``analyze_stage3_new.py``/the Stage 3 New runner
and writes condition summaries, four-cell mechanism deltas, and RTC action
composition summaries.  It does not rerun policy inference and does not claim
causal mediation.

Example
-------
python -m async_vla_benchmark.scripts.analyze_stage3_new_mechanisms \
  --results DataArchive/stage3_new_64_seeds/stage3_new/stage3_new_episode_results.csv \
  --output-dir DataArchive/stage3_new_64_seeds/analysis
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "task_key",
    "scene_condition",
    "candidate_key",
    "configured_n_action_steps",
    "added_delay_ms",
    "seed",
    "success",
    "underrun_count",
    "hold_count",
    "action_age_mean_ms",
    "action_age_p95_ms",
    "queue_occupancy_mean",
    "queue_occupancy_p95",
    "num_policy_requests",
    "rtc_mean_frozen_prefix_steps",
    "rtc_mean_guided_overlap_steps",
    "rtc_mean_fresh_suffix_steps",
}

OPTIONAL_NUMERIC = {
    "coverage_ratio_total_mean",
    "coverage_ratio_added",
    "request_latency_mean_ms",
    "request_latency_p95_ms",
}

NUMERIC_COLUMNS = {
    "configured_n_action_steps",
    "added_delay_ms",
    "seed",
    "success",
    "underrun_count",
    "hold_count",
    "action_age_mean_ms",
    "action_age_p95_ms",
    "queue_occupancy_mean",
    "queue_occupancy_p95",
    "num_policy_requests",
    "rtc_mean_frozen_prefix_steps",
    "rtc_mean_guided_overlap_steps",
    "rtc_mean_fresh_suffix_steps",
    *OPTIONAL_NUMERIC,
}


def _numeric(frame: pd.DataFrame, columns: set[str]) -> None:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")


def _validate(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required episode columns: {', '.join(missing)}")
    if len(frame) != 3456:
        raise ValueError(
            f"Expected 3,456 valid Stage 3 New rows; found {len(frame)}. "
            "Use the complete 64-seed archive or pass a separately validated file."
        )
    if set(frame["seed"].dropna().astype(int)) != set(range(46, 110)):
        raise ValueError("Stage 3 New must contain exactly seeds 46..109")
    if set(frame["configured_n_action_steps"].dropna().astype(int)) != {20, 25, 30}:
        raise ValueError("Unexpected Stage 3 New horizon set")
    if set(frame["added_delay_ms"].dropna().astype(int)) != {0, 200}:
        raise ValueError("Unexpected Stage 3 New delay set")
    if frame["run_id"].duplicated().any() if "run_id" in frame.columns else False:
        raise ValueError("Duplicate run_id values would bias the summary")


def _mean(frame: pd.DataFrame, column: str) -> float:
    if frame.empty:
        return float("nan")
    return float(frame[column].mean())


def _cell(frame: pd.DataFrame, *, task_key: str, scene: str,
          candidate_key: str | None, horizon: int, delay: int) -> pd.DataFrame:
    out = frame[
        (frame["task_key"] == task_key)
        & (frame["scene_condition"] == scene)
        & (frame["configured_n_action_steps"].astype(int) == horizon)
        & (frame["added_delay_ms"].astype(int) == delay)
    ]
    if scene == "ood":
        out = out[out["candidate_key"] == candidate_key]
    return out


def _four_cell_deltas(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    candidates = sorted(
        x for x in frame["candidate_key"].dropna().unique()
        if x != "shared_id"
    )
    for candidate in candidates:
        task_key = str(frame.loc[frame["candidate_key"] == candidate, "task_key"].iloc[0])
        for horizon in (20, 25, 30):
            cells: dict[tuple[str, int], pd.DataFrame] = {}
            for scene in ("id", "ood"):
                for delay in (0, 200):
                    cells[(scene, delay)] = _cell(
                        frame, task_key=task_key, scene=scene,
                        candidate_key=candidate, horizon=horizon, delay=delay,
                    )
            row: dict[str, object] = {
                "candidate_key": candidate,
                "task_key": task_key,
                "horizon": horizon,
            }
            metrics = {
                "success_rate": "success",
                "mean_underrun_steps": "underrun_count",
                "mean_hold_steps": "hold_count",
                "mean_action_age_ms": "action_age_mean_ms",
                "mean_action_age_p95_ms": "action_age_p95_ms",
                "mean_queue_occupancy": "queue_occupancy_mean",
                "mean_queue_occupancy_p95": "queue_occupancy_p95",
                "mean_policy_requests": "num_policy_requests",
            }
            # Episode-level any-underrun prevalence is intentionally separate
            # from the number of underrun control steps.
            for key, cell in cells.items():
                scene, delay = key
                cell = cell.copy()
                cell["underrun_any"] = (cell["underrun_count"] > 0).astype(int)
                for label, column in metrics.items():
                    row[f"{scene}_{'native' if delay == 0 else 'plus200'}_{label}"] = _mean(cell, column)
                row[f"{scene}_{'native' if delay == 0 else 'plus200'}_pct_episodes_with_underrun"] = _mean(cell, "underrun_any")
            for label in (
                "success_rate", "mean_underrun_steps", "mean_hold_steps",
                "pct_episodes_with_underrun", "mean_action_age_ms",
                "mean_action_age_p95_ms", "mean_queue_occupancy",
                "mean_queue_occupancy_p95", "mean_policy_requests",
            ):
                row[f"ood_minus_id_delay_delta_{label}"] = (
                    row[f"ood_plus200_{label}"] - row[f"ood_native_{label}"
                    ] - (row[f"id_plus200_{label}"] - row[f"id_native_{label}"])
                )
            rows.append(row)
    return pd.DataFrame(rows)


def analyze(results: Path, output_dir: Path) -> None:
    frame = pd.read_csv(results)
    _numeric(frame, NUMERIC_COLUMNS)
    _validate(frame)
    frame["underrun_any"] = (frame["underrun_count"] > 0).astype(int)

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_keys = [
        "candidate_key", "task_key", "scene_condition",
        "configured_n_action_steps", "added_delay_ms",
    ]
    summary = frame.groupby(summary_keys, dropna=False).agg(
        n=("success", "size"),
        success_rate=("success", "mean"),
        mean_underrun_steps=("underrun_count", "mean"),
        pct_episodes_with_underrun=("underrun_any", "mean"),
        mean_hold_steps=("hold_count", "mean"),
        mean_action_age_ms=("action_age_mean_ms", "mean"),
        mean_action_age_p95_ms=("action_age_p95_ms", "mean"),
        mean_queue_occupancy=("queue_occupancy_mean", "mean"),
        mean_queue_occupancy_p95=("queue_occupancy_p95", "mean"),
        mean_delay_ratio=("coverage_ratio_total_mean", "mean"),
        mean_added_delay_ratio=("coverage_ratio_added", "mean"),
        mean_policy_requests=("num_policy_requests", "mean"),
    ).reset_index()
    summary.to_csv(output_dir / "stage3_new_queue_summary.csv", index=False)

    deltas = _four_cell_deltas(frame)
    deltas.to_csv(output_dir / "stage3_new_four_cell_mechanism_deltas.csv", index=False)

    composition = frame.groupby([
        "task_key", "candidate_key", "scene_condition",
        "configured_n_action_steps", "added_delay_ms",
    ], dropna=False).agg(
        n=("success", "size"),
        success_rate=("success", "mean"),
        mean_frozen_prefix_steps=("rtc_mean_frozen_prefix_steps", "mean"),
        mean_guided_overlap_steps=("rtc_mean_guided_overlap_steps", "mean"),
        mean_fresh_suffix_steps=("rtc_mean_fresh_suffix_steps", "mean"),
        mean_action_age_ms=("action_age_mean_ms", "mean"),
        mean_queue_occupancy=("queue_occupancy_mean", "mean"),
        mean_underrun_steps=("underrun_count", "mean"),
    ).reset_index()
    composition.to_csv(output_dir / "stage3_new_rtc_action_composition.csv", index=False)

    report = f"""# Stage 3 New mechanism analysis

Input: `{results}`

- Valid episode rows: **{len(frame)}**
- Rollout seeds: **46..109 (64 per seed block)**
- This is descriptive post-processing; it does not establish causal mediation.

## Interpretation guardrails

Report action age, RTC prefix composition, queue occupancy, and underruns
alongside success. Do not claim that every delay-associated failure is caused
by queue starvation: episode duration and task difficulty can affect request
counts and timing summaries.

## Outputs

- `stage3_new_queue_summary.csv`: condition-level queue/freshness summary.
- `stage3_new_four_cell_mechanism_deltas.csv`: OOD-minus-ID delay deltas.
- `stage3_new_rtc_action_composition.csv`: frozen-prefix/guided-overlap/fresh-suffix composition.
"""
    (output_dir / "STAGE3_NEW_MECHANISM_ANALYSIS.md").write_text(report)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.results, args.output_dir)
    print(f"Wrote Stage 3 New mechanism outputs to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
