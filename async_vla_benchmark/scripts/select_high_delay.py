#!/usr/bin/env python3
"""Stage 0 — apply the frozen `d*` rule and emit the calibration tables.

    python -m async_vla_benchmark.scripts.select_high_delay \
        --results async_vla_benchmark/outputs/stage0/latency_calibration_episode_results.csv

Reads only ID calibration results. It has no code path that can see a
LIBERO-Plus outcome, which is what makes `selection_used_ood_results: false` in
the emitted JSON a statement about the program rather than about intent.

Outputs (STAGE_0 sections 8.5 and 9):
    selected_high_delay.json
    table_a_per_task_calibration.csv
    table_b_pooled_curve.csv
    table_c_method_calibration.csv
    table_d_freshness.csv
    STAGE_0_OBSERVATIONS.md
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Sequence

from async_vla_benchmark.benchmark.logging import read_csv, write_csv, write_json
from async_vla_benchmark.benchmark.stage0 import (
    ADDED_DELAYS_MS,
    EXECUTION_METHODS,
    METHOD_DISPLAY,
    STAGE0_TASKS,
    TASK_GROUP_DISPLAY,
    CalibrationRow,
    cell_viability,
    delay_display,
    select_high_delay,
    selection_payload,
    stage0_manifest,
)


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _mean(values: Sequence[float]) -> float:
    usable = [v for v in values if not math.isnan(v)]
    return sum(usable) / len(usable) if usable else math.nan


def _fmt(value: float, digits: int = 3) -> str:
    return "" if value is None or math.isnan(value) else f"{value:.{digits}f}"


def load_rows(path: Path) -> tuple[list[CalibrationRow], list[dict[str, Any]]]:
    raw = read_csv(path)
    if not raw:
        raise SystemExit(f"no rows in {path}")
    rows = [
        CalibrationRow(
            task_key=r["task_key"],
            execution_method=r["execution_method"],
            added_delay_ms=int(r["added_delay_ms"]),
            seed=int(r["seed"]),
            success=str(r.get("success", "")).strip() in {"1", "True", "true"},
            status=r.get("status", "ok") or "ok",
        )
        for r in raw
    ]
    return rows, raw


def table_a(rows: list[CalibrationRow], out: Path) -> None:
    """Per task x method success at every delay level, with a viability flag."""
    viability = {(c.task_key, c.execution_method): c for c in cell_viability(rows)}
    records = []
    for task in STAGE0_TASKS:
        for method in EXECUTION_METHODS:
            cell = viability.get((task.task_key, method))
            record = {
                "Task-demand group": TASK_GROUP_DISPLAY[task.task_group],
                "Method": METHOD_DISPLAY[method],
            }
            for delay in ADDED_DELAYS_MS:
                subset = [
                    r
                    for r in rows
                    if r.status == "ok"
                    and r.task_key == task.task_key
                    and r.execution_method == method
                    and r.added_delay_ms == delay
                ]
                successes = sum(1 for r in subset if r.success)
                record[delay_display(delay)] = (
                    f"{successes}/{len(subset)}" if subset else ""
                )
            record["Viable?"] = "yes" if cell and cell.viable else "no"
            records.append(record)
    write_csv(out, records)


def table_b(result, raw: list[dict[str, Any]], out: Path) -> None:
    """Pooled calibration curve over viable cells only."""
    viable = {f"{t}:{m}" for t, m in result.viable_cells}
    records = []
    for point in result.curve:
        matching = [
            r
            for r in raw
            if int(r["added_delay_ms"]) == point.added_delay_ms
            and f"{r['task_key']}:{r['execution_method']}" in viable
            and (r.get("status") or "ok") == "ok"
        ]
        records.append(
            {
                "Added delay": delay_display(point.added_delay_ms),
                "Success on viable ID cells": f"{point.successes}/{point.episodes}",
                "Success rate": _fmt(point.success_rate),
                "Drop from Native": _fmt(result.native_success - point.success_rate),
                "Mean request latency (ms)": _fmt(
                    _mean([_float(r["request_latency_mean_ms"]) for r in matching]), 1
                ),
                "p95 action age (ms)": _fmt(
                    _mean([_float(r["action_age_p95_ms"]) for r in matching]), 1
                ),
                "Selected": "<-- d*"
                if point.added_delay_ms == result.selected_delay_ms
                else "",
            }
        )
    write_csv(out, records)


def table_c(rows: list[CalibrationRow], out: Path) -> None:
    """Per-method curve. Descriptive only -- d* stays common to both methods."""
    records = []
    for method in EXECUTION_METHODS:
        record = {"Method": METHOD_DISPLAY[method]}
        for delay in ADDED_DELAYS_MS:
            subset = [
                r
                for r in rows
                if r.status == "ok"
                and r.execution_method == method
                and r.added_delay_ms == delay
            ]
            successes = sum(1 for r in subset if r.success)
            record[delay_display(delay)] = f"{successes}/{len(subset)}" if subset else ""
        records.append(record)
    write_csv(out, records)


def table_d(raw: list[dict[str, Any]], out: Path) -> None:
    """Freshness response: does added delay move action age and queue state?"""
    records = []
    for delay in ADDED_DELAYS_MS:
        subset = [
            r
            for r in raw
            if int(r["added_delay_ms"]) == delay and (r.get("status") or "ok") == "ok"
        ]
        if not subset:
            continue
        records.append(
            {
                "Added delay": delay_display(delay),
                "Mean request latency (ms)": _fmt(
                    _mean([_float(r["request_latency_mean_ms"]) for r in subset]), 1
                ),
                "Mean action age (ms)": _fmt(
                    _mean([_float(r["action_age_mean_ms"]) for r in subset]), 1
                ),
                "p95 action age (ms)": _fmt(
                    _mean([_float(r["action_age_p95_ms"]) for r in subset]), 1
                ),
                "Mean logical delay (steps)": _fmt(
                    _mean([_float(r["logical_delay_steps_mean"]) for r in subset]), 2
                ),
                "Mean queue occupancy": _fmt(
                    _mean([_float(r["queue_occupancy_mean"]) for r in subset]), 2
                ),
                "Underruns": _fmt(
                    _mean([_float(r["underrun_count"]) for r in subset]), 1
                ),
                "Holds": _fmt(_mean([_float(r["hold_count"]) for r in subset]), 1),
            }
        )
    write_csv(out, records)


def observations(result, rows: list[CalibrationRow], raw, out: Path) -> None:
    viability = cell_viability(rows)
    invalid = [r for r in raw if (r.get("status") or "ok") != "ok"]
    lines = [
        "# Latency Calibration Observations",
        "",
        "Generated by `scripts/select_high_delay.py`. Do not edit numbers by hand.",
        "",
        "## Coverage",
        "",
        f"- episodes on disk: {len(raw)}",
        f"- valid: {len(raw) - len(invalid)}",
        f"- invalid: {len(invalid)}",
        "",
        "## Native ID viability",
        "",
        "| Task | Method | Native success | Viable |",
        "|---|---|---|---|",
    ]
    for cell in viability:
        lines.append(
            f"| {cell.task_key} | {METHOD_DISPLAY.get(cell.execution_method, cell.execution_method)} "
            f"| {cell.native_successes}/{cell.native_episodes} "
            f"| {'yes' if cell.viable else 'no'} |"
        )
    lines += [
        "",
        "## Delay-response curve (viable cells only)",
        "",
        "| Added delay | Success | Rate | Drop from Native |",
        "|---|---|---|---|",
    ]
    for point in result.curve:
        lines.append(
            f"| {delay_display(point.added_delay_ms)} "
            f"| {point.successes}/{point.episodes} "
            f"| {_fmt(point.success_rate)} "
            f"| {_fmt(result.native_success - point.success_rate)} |"
        )
    lines += [
        "",
        "## Selected high delay",
        "",
        f"- **d\\* = {result.selected_delay_ms} ms**",
        f"- rule applied: `{result.rule_applied}`",
        f"- pooled Native success: {_fmt(result.native_success)}",
        f"- pooled success at d\\*: {_fmt(result.selected_success)}",
        f"- drop: {_fmt(result.success_drop)}",
        f"- viable cells: {len(result.viable_cells)}",
        "",
        "## Data-quality warnings",
        "",
    ]
    warnings = list(result.notes)
    if invalid:
        warnings.append(f"{len(invalid)} invalid episode(s); see `status`/`invalid_reason`.")
    if result.calibration_saturated:
        warnings.append("CALIBRATION_SATURATED is set.")
    if result.calibration_weak:
        warnings.append("CALIBRATION_WEAK is set.")
    lines.extend(f"- {w}" for w in warnings or ["none"])
    lines.append("")
    out.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="defaults to the directory holding --results",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail if fewer than the full planned grid of valid episodes is present",
    )
    args = parser.parse_args()

    out_dir = args.output_dir or args.results.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, raw = load_rows(args.results)
    valid = [r for r in rows if r.status == "ok"]
    # Derive from SEEDS rather than a literal: this was `* 2` and would have
    # accepted a third of the grid as "complete" once Stage 0 moved to six seeds.
    expected = len(stage0_manifest())
    if args.require_complete and len(valid) < expected:
        raise SystemExit(
            f"{len(valid)}/{expected} valid episodes; rerun the gaps or drop "
            "--require-complete to calibrate on a partial grid"
        )

    result = select_high_delay(rows)

    write_json(out_dir / "selected_high_delay.json", selection_payload(result))
    table_a(rows, out_dir / "table_a_per_task_calibration.csv")
    table_b(result, raw, out_dir / "table_b_pooled_curve.csv")
    table_c(rows, out_dir / "table_c_method_calibration.csv")
    table_d(raw, out_dir / "table_d_freshness.csv")
    observations(result, rows, raw, out_dir / "STAGE_0_OBSERVATIONS.md")

    print(f"episodes: {len(valid)} valid / {len(rows)} total (expected {expected})")
    print(f"viable cells: {len(result.viable_cells)} of {len(STAGE0_TASKS) * len(EXECUTION_METHODS)}")
    print(f"pooled Native success: {_fmt(result.native_success)}")
    for point in result.curve:
        marker = " <-- d*" if point.added_delay_ms == result.selected_delay_ms else ""
        print(
            f"  {delay_display(point.added_delay_ms):>18}: "
            f"{point.successes}/{point.episodes} = {_fmt(point.success_rate)}{marker}"
        )
    print(f"\nd* = {result.selected_delay_ms} ms  (rule: {result.rule_applied})")
    for note in result.notes:
        print(f"WARN {note}")
    print(f"\nwrote selected_high_delay.json and 4 tables to {out_dir}")

    # Nonzero exit on a flagged calibration: Stage 1 is still runnable, but the
    # decision to proceed should be deliberate rather than implied by silence.
    if result.calibration_weak or result.calibration_saturated or result.insufficient_viable_cells:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
