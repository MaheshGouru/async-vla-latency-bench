#!/usr/bin/env python3
"""Validate Stage 0 outputs, select d*, and generate paper-facing artifacts."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

from async_vla_benchmark.benchmark.config import BenchmarkConfig, load_config
from async_vla_benchmark.benchmark.logging import write_csv, write_json
from async_vla_benchmark.benchmark.stage0 import select_high_delay, stage0_plans
from async_vla_benchmark.scripts.validate_results import validate_episode


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "stage0_latency_calibration.yaml"


def _finite(values: Iterable[Any]) -> list[float]:
    result = []
    for value in values:
        if value is None:
            continue
        number = float(value)
        if math.isfinite(number):
            result.append(number)
    return result


def _mean(values: Iterable[Any]) -> float:
    finite = _finite(values)
    return statistics.mean(finite) if finite else float("nan")


def _sum(values: Iterable[Any]) -> int:
    return int(sum(float(value) for value in values if value is not None))


def _episode_result_row(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": summary["run_id"],
        "task_key": summary["task_key"],
        "task_group": summary["task_group_label"],
        "suite": summary["suite"],
        "task_id": summary["task_id"],
        "task_name": summary["task_name"],
        "execution_method": summary["execution_method"],
        "added_delay_ms": summary["added_delay_ms"],
        "seed": summary["seed"],
        "success": summary["success"],
        "episode_steps": summary["environment_steps"],
        "completion_fraction": summary.get("completion_fraction"),
        "request_latency_mean_ms": summary["mean_request_latency_ms"],
        "request_latency_p50_ms": summary["p50_request_latency_ms"],
        "request_latency_p95_ms": summary["p95_request_latency_ms"],
        "action_age_mean_ms": summary["mean_action_age_ms"],
        "action_age_p50_ms": summary["p50_action_age_ms"],
        "action_age_p95_ms": summary["p95_action_age_ms"],
        "action_age_max_ms": summary["maximum_action_age_ms"],
        "logical_delay_steps_mean": summary["mean_logical_delay_steps"],
        "logical_delay_steps_p95": summary["p95_logical_delay_steps"],
        "queue_occupancy_mean": summary["mean_queue_depth"],
        "queue_occupancy_p95": summary["p95_queue_depth"],
        "underrun_count": summary["queue_underrun_steps"],
        "hold_count": summary["hold_action_steps"],
        "discard_count": summary["discarded_old_actions"],
        "num_policy_requests": summary["number_of_policy_requests"],
        "action_delta_mean": summary["mean_action_delta_l2"],
        "action_accel_mean": summary["mean_action_acceleration_l2"],
        "action_jerk_mean": summary["mean_action_jerk_l2"],
        "wall_clock_episode_s": summary["wall_clock_runtime_seconds"],
        "gpu_id": summary.get("gpu_id"),
        "status": summary.get("status", "completed"),
        "invalid_reason": summary.get("invalid_reason"),
    }


def _cell_rows(
    rows: list[dict[str, Any]],
    *,
    task_key: str | None = None,
    method: str | None = None,
    delay: int | None = None,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (task_key is None or row["task_key"] == task_key)
        and (method is None or row["execution_method"] == method)
        and (delay is None or int(row["added_delay_ms"]) == delay)
    ]


def _count_label(rows: list[dict[str, Any]]) -> str:
    return f"{sum(bool(row['success']) for row in rows)}/{len(rows)}"


def _viable_cells(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    keys = {(row["task_key"], row["execution_method"]) for row in rows}
    return {
        key
        for key in keys
        if sum(bool(row["success"]) for row in _cell_rows(
            rows, task_key=key[0], method=key[1], delay=0
        ))
        >= 1
    }


def _write_tables(
    cfg: BenchmarkConfig,
    output_dir: Path,
    rows: list[dict[str, Any]],
    selection: dict[str, Any],
) -> None:
    assert cfg.stage0 is not None
    viable = _viable_cells(rows)
    delays = cfg.stage0.added_delays_ms

    per_task = []
    for task in cfg.stage0.tasks:
        for method in cfg.stage0.methods:
            row = {
                "task_group": task.task_group_label,
                "task_key": task.task_key,
                "execution_method": method,
            }
            for delay in delays:
                row[f"delay_{delay}_success"] = _count_label(
                    _cell_rows(rows, task_key=task.task_key, method=method, delay=delay)
                )
            row["viable"] = (task.task_key, method) in viable
            per_task.append(row)
    write_csv(output_dir / "latency_calibration_table_per_task.csv", per_task)

    pooled = []
    for curve_row in selection["curve"]:
        delay = int(curve_row["added_delay_ms"])
        eligible = [
            row
            for row in rows
            if int(row["added_delay_ms"]) == delay
            and (row["task_key"], row["execution_method"]) in viable
        ]
        pooled.append(
            {
                **curve_row,
                "mean_request_latency_ms": _mean(
                    row["request_latency_mean_ms"] for row in eligible
                ),
                "mean_episode_p95_action_age_ms": _mean(
                    row["action_age_p95_ms"] for row in eligible
                ),
                "selected": delay == selection["high_added_delay_ms"],
            }
        )
    write_csv(output_dir / "latency_calibration_table_pooled.csv", pooled)

    by_method = []
    for method in cfg.stage0.methods:
        row = {"execution_method": method}
        for delay in delays:
            row[f"delay_{delay}_success"] = _count_label(
                _cell_rows(rows, method=method, delay=delay)
            )
        by_method.append(row)
    write_csv(output_dir / "latency_calibration_table_method.csv", by_method)

    freshness = []
    for delay in delays:
        for method in cfg.stage0.methods:
            cell = _cell_rows(rows, method=method, delay=delay)
            freshness.append(
                {
                    "added_delay_ms": delay,
                    "execution_method": method,
                    "action_age_mean_ms": _mean(row["action_age_mean_ms"] for row in cell),
                    "action_age_p95_ms": _mean(row["action_age_p95_ms"] for row in cell),
                    "logical_delay_steps_p95": _mean(
                        row["logical_delay_steps_p95"] for row in cell
                    ),
                    "underrun_count": _sum(row["underrun_count"] for row in cell),
                    "discard_count": _sum(row["discard_count"] for row in cell),
                }
            )
    write_csv(output_dir / "latency_calibration_table_freshness.csv", freshness)


def _write_observations(
    cfg: BenchmarkConfig,
    output_dir: Path,
    rows: list[dict[str, Any]],
    missing: list[str],
    invalid: list[str],
    selection: dict[str, Any] | None,
) -> None:
    assert cfg.stage0 is not None
    viable = _viable_cells(rows)
    lines = [
        "# Latency Calibration Observations",
        "",
        "## Coverage",
        "- Expected episodes: 96",
        f"- Completed and valid: {len(rows)}",
        f"- Missing: {len(missing)}",
        f"- Invalid: {len(invalid)}",
        "",
        "## Native ID viability",
    ]
    for task in cfg.stage0.tasks:
        lines.append(f"### {task.task_group_label}")
        for method in cfg.stage0.methods:
            native = _cell_rows(rows, task_key=task.task_key, method=method, delay=0)
            lines.append(
                f"- {method}: {_count_label(native)}; "
                f"viable={(task.task_key, method) in viable}"
            )
        lines.append("")

    lines.extend(["## Delay-response curve"])
    if selection is None:
        lines.append("- Not available until all 96 episodes are valid.")
    else:
        for point in selection["curve"]:
            lines.append(
                f"- +{point['added_delay_ms']} ms pooled success: "
                f"{point['successful_episodes']}/{point['episodes']} ({point['success']:.3f})"
            )
        lines.extend(
            [
                "",
                "## Selected high delay",
                f"- d*: {selection['high_added_delay_ms']} ms",
                f"- Selection reason: {selection['selection_reason']}",
                f"- Calibration saturated: {selection['calibration_saturated']}",
                f"- Calibration weak: {selection['calibration_weak']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Data-quality warnings",
            "- Failed episodes have no calibrated subgoal-progress signal; "
            "completion_fraction is left null rather than inferred from elapsed steps.",
            "- Hold actions have no source observation and are excluded from action-age aggregates.",
        ]
    )
    if missing:
        lines.append(f"- Missing episode IDs: {', '.join(missing)}")
    if invalid:
        lines.append(f"- Invalid episode IDs: {', '.join(invalid)}")
    (output_dir / "LATENCY_CALIBRATION_OBSERVATIONS.md").write_text("\n".join(lines) + "\n")


def _plot_stage0(
    cfg: BenchmarkConfig,
    output_dir: Path,
    rows: list[dict[str, Any]],
    selection: dict[str, Any],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assert cfg.stage0 is not None
    colors = {"naive_async": "#2563eb", "rtc": "#dc2626"}
    delays = cfg.stage0.added_delays_ms

    def task_facets(metric: str, ylabel: str, filename: str, success: bool = False) -> None:
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
        for ax, task in zip(axes, cfg.stage0.tasks):
            for method in cfg.stage0.methods:
                values = []
                for delay in delays:
                    cell = _cell_rows(rows, task_key=task.task_key, method=method, delay=delay)
                    values.append(
                        sum(bool(row["success"]) for row in cell) / len(cell)
                        if success
                        else _mean(row[metric] for row in cell)
                    )
                ax.plot(delays, values, marker="o", label=method, color=colors[method])
            ax.set_title(task.task_group_label)
            ax.set_xlabel("Added delay (ms)")
            ax.grid(alpha=0.25)
        axes[0].set_ylabel(ylabel)
        axes[-1].legend(frameon=False)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=180)
        plt.close(fig)

    task_facets(
        "success",
        "Success rate",
        "latency_calibration_success_by_task.png",
        success=True,
    )
    task_facets(
        "action_age_p95_ms",
        "Episode p95 action age (ms)",
        "latency_calibration_action_age.png",
    )

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(
        [point["added_delay_ms"] for point in selection["curve"]],
        [point["success"] for point in selection["curve"]],
        marker="o",
        color="#111827",
    )
    ax.axvline(selection["high_added_delay_ms"], color="#dc2626", linestyle="--", label="selected d*")
    ax.set(xlabel="Added delay (ms)", ylabel="Pooled success on viable ID cells", ylim=(-0.03, 1.03))
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "latency_calibration_pooled_curve.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for method in cfg.stage0.methods:
        values = [
            _mean(
                row["logical_delay_steps_mean"]
                for row in _cell_rows(rows, method=method, delay=delay)
            )
            for delay in delays
        ]
        ax.plot(delays, values, marker="o", label=method, color=colors[method])
    ax.set(xlabel="Added delay (ms)", ylabel="Mean logical delay (control steps)")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "latency_calibration_logical_steps.png", dpi=180)
    plt.close(fig)


def build_stage0_artifacts(
    cfg: BenchmarkConfig,
    output_dir: Path,
    *,
    require_complete: bool = True,
) -> int:
    plans = stage0_plans(cfg)
    rows = []
    missing = []
    invalid = []
    for plan in plans:
        path = output_dir / "episodes" / f"{plan.episode_id}.json"
        if not path.exists():
            missing.append(plan.episode_id)
            continue
        summary = json.loads(path.read_text())
        errors = validate_episode(output_dir, plan.episode_id, summary)
        if summary.get("run_id") != plan.run_id:
            errors.append(f"run_id {summary.get('run_id')!r} != {plan.run_id!r}")
        if summary.get("task_name") != plan.task.task_name:
            errors.append(
                f"task_name {summary.get('task_name')!r} != {plan.task.task_name!r}"
            )
        if errors:
            invalid.append(plan.episode_id)
            summary["status"] = "invalid"
            summary["invalid_reason"] = " | ".join(errors)
        rows.append(_episode_result_row(summary))

    write_csv(output_dir / "latency_calibration_episode_results.csv", rows)
    valid_rows = [row for row in rows if row["status"] == "completed"]
    if missing or invalid or len(valid_rows) != 96:
        _write_observations(cfg, output_dir, valid_rows, missing, invalid, None)
        print(
            f"Stage 0 coverage: valid={len(valid_rows)}/96 missing={len(missing)} "
            f"invalid={len(invalid)}"
        )
        return 1 if require_complete else 0

    selection = select_high_delay(valid_rows)
    write_json(output_dir / "selected_high_delay.json", selection)
    _write_tables(cfg, output_dir, valid_rows, selection)
    _write_observations(cfg, output_dir, valid_rows, missing, invalid, selection)
    _plot_stage0(cfg, output_dir, valid_rows, selection)
    print(
        f"Stage 0 complete: 96/96 valid; selected d*={selection['high_added_delay_ms']} ms "
        f"via {selection['selection_reason']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    return build_stage0_artifacts(
        load_config(args.config),
        args.output_dir,
        require_complete=not args.allow_partial,
    )


if __name__ == "__main__":
    raise SystemExit(main())
