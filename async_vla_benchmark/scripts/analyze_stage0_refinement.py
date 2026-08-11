#!/usr/bin/env python3
"""Combine the 25/50/75 ms refinement with Stage 0's 0/100 ms boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from async_vla_benchmark.benchmark.config import BenchmarkConfig, load_config
from async_vla_benchmark.benchmark.logging import write_csv, write_json
from async_vla_benchmark.benchmark.stage0 import (
    REFINEMENT_CELLS,
    REFINEMENT_DELAYS_MS,
    REFINEMENT_SEEDS,
    select_high_delay,
    stage0_plans,
    stage0_refinement_plans,
)
from async_vla_benchmark.scripts.analyze_stage0 import (
    _episode_result_row,
    _mean,
    _viable_cells,
)
from async_vla_benchmark.scripts.validate_results import validate_episode


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "stage0_latency_calibration.yaml"
REFINED_GRID_MS = (0, *REFINEMENT_DELAYS_MS, 100)


def _load_summaries(
    output_dir: Path,
    plans: Iterable,
    *,
    require_complete: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    summaries = []
    errors = []
    for plan in plans:
        path = output_dir / "episodes" / f"{plan.episode_id}.json"
        if not path.exists():
            if require_complete:
                errors.append(f"missing {path}")
            continue
        summary = json.loads(path.read_text())
        validation_errors = validate_episode(output_dir, plan.episode_id, summary)
        if validation_errors:
            errors.extend(f"{plan.episode_id}: {error}" for error in validation_errors)
            continue
        summaries.append(summary)
    return summaries, errors


def _base_boundary_plans(cfg: BenchmarkConfig):
    cells = set(REFINEMENT_CELLS)
    return [
        plan
        for plan in stage0_plans(cfg)
        if (plan.task.task_key, plan.execution_method) in cells
        and plan.added_delay_ms in (0, 100)
        and plan.seed in REFINEMENT_SEEDS
    ]


def build_stage0_refinement_artifacts(
    cfg: BenchmarkConfig,
    output_dir: Path,
    base_output_dir: Path,
    *,
    require_complete: bool,
) -> int:
    refinement_plans = stage0_refinement_plans(cfg)
    new_summaries, new_errors = _load_summaries(
        output_dir, refinement_plans, require_complete=require_complete
    )
    base_summaries, base_errors = _load_summaries(
        base_output_dir, _base_boundary_plans(cfg), require_complete=require_complete
    )
    errors = [*new_errors, *base_errors]
    if errors:
        print("Stage 0 refinement validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    new_rows = [_episode_result_row(summary) for summary in new_summaries]
    write_csv(output_dir / "latency_refinement_episode_results.csv", new_rows)
    if not require_complete:
        print(
            f"Stage 0 refinement partial: {len(new_summaries)}/{len(refinement_plans)} "
            "new episodes; final selection deferred"
        )
        return 0

    combined_rows = [
        *[_episode_result_row(summary) for summary in base_summaries],
        *new_rows,
    ]
    selection = select_high_delay(combined_rows, REFINED_GRID_MS)
    selection["source_stage0_boundary_delays_ms"] = [0, 100]
    selection["new_refinement_delays_ms"] = list(REFINEMENT_DELAYS_MS)
    selection["new_refinement_episodes"] = len(new_rows)
    selection["seeds"] = list(REFINEMENT_SEEDS)
    write_json(output_dir / "selected_high_delay_refined.json", selection)

    viable = _viable_cells(combined_rows)
    curve_rows = []
    for point in selection["curve"]:
        delay = int(point["added_delay_ms"])
        eligible = [
            row
            for row in combined_rows
            if int(row["added_delay_ms"]) == delay
            and (row["task_key"], row["execution_method"]) in viable
        ]
        curve_rows.append(
            {
                **point,
                "mean_request_latency_ms": _mean(
                    row["request_latency_mean_ms"] for row in eligible
                ),
                "mean_action_age_ms": _mean(row["action_age_mean_ms"] for row in eligible),
                "mean_p95_action_age_ms": _mean(
                    row["action_age_p95_ms"] for row in eligible
                ),
                "total_underrun_steps": sum(int(row["underrun_count"]) for row in eligible),
                "selected": delay == selection["high_added_delay_ms"],
            }
        )
    write_csv(output_dir / "latency_refinement_combined_curve.csv", curve_rows)

    cell_rows = []
    for task_key, method in REFINEMENT_CELLS:
        row: dict[str, Any] = {"task_key": task_key, "execution_method": method}
        for delay in REFINED_GRID_MS:
            cell = [
                item
                for item in combined_rows
                if item["task_key"] == task_key
                and item["execution_method"] == method
                and int(item["added_delay_ms"]) == delay
            ]
            row[f"delay_{delay}_success"] = (
                f"{sum(bool(item['success']) for item in cell)}/{len(cell)}"
            )
        cell_rows.append(row)
    write_csv(output_dir / "latency_refinement_by_cell.csv", cell_rows)

    report = [
        "# Stage 0 Latency Refinement",
        "",
        "## Coverage",
        f"- New episodes: {len(new_rows)}/18",
        "- Reused Stage 0 boundary episodes: 12/12",
        "- Added-delay grid: 0, 25, 50, 75, 100 ms",
        "- Seeds: 0, 1",
        "",
        "## Pooled viable-cell curve",
    ]
    for point in curve_rows:
        report.append(
            f"- +{point['added_delay_ms']} ms: "
            f"{point['successful_episodes']}/{point['episodes']} "
            f"({point['success']:.3f})"
        )
    report.extend(
        [
            "",
            "## Refined selection",
            f"- d*: {selection['high_added_delay_ms']} ms",
            f"- Reason: {selection['selection_reason']}",
            "",
            "## Limitation",
            "- This remains a two-seed refinement and should be treated as preliminary.",
        ]
    )
    (output_dir / "LATENCY_REFINEMENT_OBSERVATIONS.md").write_text(
        "\n".join(report) + "\n"
    )
    print(
        f"Stage 0 refinement complete: 18/18 valid; selected "
        f"d*={selection['high_added_delay_ms']} ms via {selection['selection_reason']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-output-dir", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    return build_stage0_refinement_artifacts(
        cfg,
        args.output_dir,
        args.base_output_dir,
        require_complete=not args.allow_partial,
    )


if __name__ == "__main__":
    raise SystemExit(main())
