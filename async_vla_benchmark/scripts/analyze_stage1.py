#!/usr/bin/env python3
"""Generate the seven Stage 1 tables, interaction plots, and observations."""

import argparse
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage1 import PERTURBATIONS, TASK_GROUP_LABELS, interaction


def _rate(rows):
    return sum(int(r["success"]) for r in rows) / len(rows) if rows else float("nan")


def _mean(rows, key):
    values = [float(r[key]) for r in rows if r.get(key, "") not in ("", "nan")]
    return sum(values) / len(values) if values else float("nan")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    rows = [r for r in read_csv(args.results) if r.get("status", "").startswith("ok")]
    if len(rows) != 480 and not args.allow_incomplete:
        raise ValueError(f"refusing analysis of incomplete matrix: {len(rows)}/480")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    id_rows = [r for r in rows if r["scene_condition"] == "id"]
    ood_rows = [r for r in rows if r["scene_condition"] == "ood"]

    coverage = []
    for task in sorted({r["task_key"] for r in ood_rows}):
        for perturbation in PERTURBATIONS:
            subset = [r for r in ood_rows if r["task_key"] == task and r["perturbation_key"] == perturbation.key]
            coverage.append({"task": task, "task_group": subset[0]["task_group"] if subset else "", "perturbation": perturbation.key,
                "mechanism_group": perturbation.mechanism_key, "intended_episodes": 20, "completed": len(subset),
                "invalid": max(0, 20-len(subset))})
    write_csv(args.output_dir / "stage1_table_coverage.csv", coverage)

    four = []
    for task in sorted({r["task_key"] for r in ood_rows}):
        for perturbation in PERTURBATIONS:
            for method in ("naive_async", "rtc"):
                base = [r for r in id_rows if r["task_key"] == task and r["execution_method"] == method]
                shifted = [r for r in ood_rows if r["task_key"] == task and r["perturbation_key"] == perturbation.key and r["execution_method"] == method]
                il, ih = _rate([r for r in base if r["delay_condition"] == "low"]), _rate([r for r in base if r["delay_condition"] == "high"])
                ol, oh = _rate([r for r in shifted if r["delay_condition"] == "low"]), _rate([r for r in shifted if r["delay_condition"] == "high"])
                four.append({"task": task, "task_group": base[0]["task_group"] if base else "", "perturbation": perturbation.key,
                    "mechanism_group": perturbation.mechanism_key, "method": method, "id_low": il, "id_high": ih,
                    "ood_low": ol, "ood_high": oh, "interaction_I": interaction(il, ih, ol, oh)})
    write_csv(args.output_dir / "stage1_table_four_cell.csv", four)

    perturbation_table = []
    for perturbation in PERTURBATIONS:
        for method in ("naive_async", "rtc"):
            subset = [r for r in four if r["perturbation"] == perturbation.key and r["method"] == method]
            perturbation_table.append({"perturbation": perturbation.key, "mechanism_group": perturbation.mechanism_key, "method": method,
                "id_delay_drop": sum(r["id_high"]-r["id_low"] for r in subset)/len(subset),
                "ood_delay_drop": sum(r["ood_high"]-r["ood_low"] for r in subset)/len(subset),
                "pooled_I": sum(r["interaction_I"] for r in subset)/len(subset), "ood_low_success": sum(r["ood_low"] for r in subset)/len(subset)})
    write_csv(args.output_dir / "stage1_table_perturbation_summary.csv", perturbation_table)

    mechanism_table = []
    for mechanism in sorted({p.mechanism_key for p in PERTURBATIONS}):
        for method in ("naive_async", "rtc"):
            subset = [r for r in perturbation_table if r["mechanism_group"] == mechanism and r["method"] == method]
            mechanism_table.append({"mechanism_group": mechanism, "perturbations_included": ";".join(r["perturbation"] for r in subset),
                "method": method, "mean_I": sum(r["pooled_I"] for r in subset)/len(subset), "interpretation": "exploratory/descriptive"})
    write_csv(args.output_dir / "stage1_table_mechanism_summary.csv", mechanism_table)

    task_table = []
    for task in sorted({r["task"] for r in four}):
        for method in ("naive_async", "rtc"):
            subset = [r for r in four if r["task"] == task and r["method"] == method]
            ranked = sorted(subset, key=lambda r: r["interaction_I"])
            task_table.append({"task": task, "task_group": subset[0]["task_group"], "method": method,
                "mean_I": sum(r["interaction_I"] for r in subset)/len(subset), "strongest_perturbation": ranked[0]["perturbation"],
                "weakest_perturbation": ranked[-1]["perturbation"]})
    write_csv(args.output_dir / "stage1_table_task_group_summary.csv", task_table)

    method_table = []
    for task in sorted({r["task"] for r in four}):
        for perturbation in PERTURBATIONS:
            naive = next(r for r in four if r["task"] == task and r["perturbation"] == perturbation.key and r["method"] == "naive_async")
            rtc = next(r for r in four if r["task"] == task and r["perturbation"] == perturbation.key and r["method"] == "rtc")
            id_pref = "rtc" if rtc["id_high"] > naive["id_high"] else "naive_async"
            ood_pref = "rtc" if rtc["ood_high"] > naive["ood_high"] else "naive_async"
            method_table.append({"task": task, "perturbation": perturbation.key, "I_naive": naive["interaction_I"], "I_rtc": rtc["interaction_I"],
                "rtc_minus_naive": rtc["interaction_I"]-naive["interaction_I"], "ranking_change": id_pref != ood_pref})
    write_csv(args.output_dir / "stage1_table_method_comparison.csv", method_table)

    freshness = []
    groups = defaultdict(list)
    for row in ood_rows: groups[(row["task_key"], row["perturbation_key"], row["execution_method"], row["delay_condition"])].append(row)
    for key, subset in sorted(groups.items()):
        freshness.append({"task": key[0], "perturbation": key[1], "method": key[2], "delay": key[3], "success": _rate(subset),
            "mean_action_age": _mean(subset, "action_age_mean_ms"), "p95_action_age": _mean(subset, "action_age_p95_ms"),
            "p95_queue_occupancy": _mean(subset, "queue_occupancy_p95"), "underruns": sum(int(r["underrun_count"]) for r in subset)})
    write_csv(args.output_dir / "stage1_table_freshness.csv", freshness)

    observations = args.output_dir / "STAGE_1_OBSERVATIONS.md"
    observations.write_text("# Stage 1 Observations\n\n## 1. Coverage\n" f"- Completed: {len(rows)}/480\n- Invalid: {480-len(rows)}\n- Missing: {480-len(rows)}\n\n"
        "## 2. Overall OOD × Delay Pattern\n" f"- ID-low success: {_rate([r for r in id_rows if r['delay_condition']=='low']):.3f}\n"
        f"- ID-high success: {_rate([r for r in id_rows if r['delay_condition']=='high']):.3f}\n"
        f"- OOD-low success: {_rate([r for r in ood_rows if r['delay_condition']=='low']):.3f}\n"
        f"- OOD-high success: {_rate([r for r in ood_rows if r['delay_condition']=='high']):.3f}\n\n"
        "## 3. By Perturbation Family\nGenerated in `stage1_table_perturbation_summary.csv`.\n\n"
        "## 4. By Behavioral Demand\nGenerated in `stage1_table_task_group_summary.csv`.\n\n"
        "## 5. Execution-Method Effects\nGenerated in `stage1_table_method_comparison.csv`.\n\n"
        "## 6. Temporal-Freshness Diagnostics\nGenerated in `stage1_table_freshness.csv`.\n\n"
        "## 7. Candidate Confirmatory Effects\nPending frozen selection rule.\n\n## 8. Null / Counterintuitive Results\nReview all rows.\n\n"
        "## 9. Data-Quality Warnings\n- Stage 0 seed-0/1 controls were reused without immutable runtime identity metadata.\n")
    print(f"wrote Stage 1 analysis artifacts to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
