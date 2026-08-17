#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path

from async_vla_benchmark.benchmark.experiment_b import (
    ANALYSIS_STATUS, BASE_TASK_NAME, HORIZON, paired_interaction_values,
    validate_experiment_a_gate, validate_frozen_variants,
)
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.scripts.analyze_stage3 import paired_cluster_bootstrap, wilson


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--experiment-a-gate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    gate_hash = validate_experiment_a_gate(args.experiment_a_gate)
    validation = json.loads(args.validation.read_text())
    if validation.get("status") != "pass" or validation.get("experiment_a_dispatch_gate_sha256") != gate_hash:
        raise ValueError("Experiment B analysis requires a passing gate-bound validation record")
    rows = read_csv(args.results); variants = read_csv(args.variants); validate_frozen_variants(variants)
    if len(rows) != 64 or len({row["run_id"] for row in rows}) != 64 or any(not row.get("status", "").startswith("ok") for row in rows):
        raise ValueError("Experiment B analysis requires 64 unique valid rows")
    if {row.get("analysis_status") for row in rows} != {ANALYSIS_STATUS}:
        raise ValueError("Experiment B analysis-status provenance mismatch")
    args.output_dir.mkdir(parents=True, exist_ok=True); four_cell = []; interactions = []
    write_csv(args.output_dir / "experiment_b_unique_episode_accounting.csv", sorted(rows, key=lambda row: row["run_id"]))

    for variant in variants:
        name = variant["variant_name"]
        record = {
            "classification_id": variant["classification_id"], "api_task_index": variant["api_task_index"],
            "difficulty_level": variant["difficulty_level"], "variant_name": name,
            "analysis_status": ANALYSIS_STATUS, "configured_n_action_steps": HORIZON,
        }
        for scene in ("id", "ood"):
            target = BASE_TASK_NAME if scene == "id" else name
            for delay, label in ((0, "native"), (200, "plus_200")):
                cell = [row for row in rows if row["scene_condition"] == scene and row["variant_name"] == target and int(row["added_delay_ms"]) == delay]
                successes = sum(int(row["success"]) for row in cell); low, high = wilson(successes, len(cell)); prefix = f"{scene}_{label}"
                record.update({prefix + "_successes": successes, prefix + "_trials": len(cell), prefix + "_rate": successes / len(cell), prefix + "_wilson95_low": low, prefix + "_wilson95_high": high})
        paired = paired_interaction_values(rows, name)
        interaction = (record["ood_plus_200_rate"] - record["ood_native_rate"]) - (record["id_plus_200_rate"] - record["id_native_rate"])
        low, high = paired_cluster_bootstrap(paired)
        four_cell.append(record)
        interactions.append({
            "classification_id": variant["classification_id"], "variant_name": name,
            "difficulty_level": variant["difficulty_level"], "analysis_status": ANALYSIS_STATUS,
            "interaction_I_variant": interaction, "paired_seed_values": ";".join(map(str, paired)),
            "paired_bootstrap95_low": low, "paired_bootstrap95_high": high,
        })
    write_csv(args.output_dir / "experiment_b_four_cell_by_variant.csv", four_cell)
    write_csv(args.output_dir / "experiment_b_interaction_by_variant.csv", interactions)
    summary = {
        "experiment": "experiment_b", "analysis_status": ANALYSIS_STATUS,
        "negative_variants": sum(float(row["interaction_I_variant"]) < 0 for row in interactions),
        "zero_variants": sum(float(row["interaction_I_variant"]) == 0 for row in interactions),
        "positive_variants": sum(float(row["interaction_I_variant"]) > 0 for row in interactions),
        "mean_interaction": sum(float(row["interaction_I_variant"]) for row in interactions) / 3,
        "experiment_a_dispatch_gate_sha256": gate_hash,
        "experiment_b_validation_sha256": hashlib.sha256(args.validation.read_bytes()).hexdigest(),
        "experiment_b_results_sha256": hashlib.sha256(args.results.read_bytes()).hexdigest(),
        "frozen_variants_sha256": hashlib.sha256(args.variants.read_bytes()).hexdigest(),
    }
    (args.output_dir / "experiment_b_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    os.environ["MPLBACKEND"] = "Agg"
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axis = plt.subplots(figsize=(7, 4))
    axis.bar([f"c{row['classification_id']}" for row in interactions], [float(row["interaction_I_variant"]) for row in interactions])
    axis.axhline(0, color="black", linewidth=1)
    axis.set(ylabel="OOD × delay interaction", title="Experiment B: cross-task layout variants")
    fig.tight_layout(); fig.savefig(args.output_dir / "experiment_b_interaction_by_variant.png", dpi=180); plt.close(fig)
    lines = [
        "# Experiment B Observations", "",
        f"- Negative interactions: {summary['negative_variants']}/3.",
        f"- Mean interaction: {summary['mean_interaction']:+.3f}.",
        "- These results concern the frozen additional multi-stage task only; no task substitution or adaptive expansion was performed.", "",
    ]
    for row in interactions:
        lines.append(f"- c{row['classification_id']}: I={float(row['interaction_I_variant']):+.3f}, paired bootstrap 95% CI [{float(row['paired_bootstrap95_low']):+.3f}, {float(row['paired_bootstrap95_high']):+.3f}].")
    (args.output_dir / "EXPERIMENT_B_OBSERVATIONS.md").write_text("\n".join(lines) + "\n")
    print("PASS: complete Experiment B cross-task analysis generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
