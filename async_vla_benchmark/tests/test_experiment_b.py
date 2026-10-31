import json
from collections import Counter
from pathlib import Path

import pytest

from async_vla_benchmark.benchmark.experiment_b import (
    ANALYSIS_STATUS, BASE_TASK_NAME, DELAYS, HORIZON, SEEDS,
    experiment_b_manifest, paired_interaction_values, select_variant_entries, validate_experiment_a_gate,
)

PROVENANCE = {"git_sha": "a" * 40, "lerobot_git_sha": "b" * 40, "libero_plus_git_sha": "c" * 40, "model_revision": "d" * 40}


def variants():
    return [{
        "task_key": "additional_multistage_task", "suite": "libero_10", "base_task_id": "0",
        "base_task_name": BASE_TASK_NAME, "task_demand_type": "multi_stage_sequential",
        "perturbation_key": "object_layout", "official_category": "Objects Layout",
        "mechanism_group": "trajectory_adaptation", "classification_id": str(3000 + index),
        "api_task_index": str(3100 + index), "difficulty_level": "2",
        "variant_name": f"{BASE_TASK_NAME}_layout_{index}",
    } for index in range(3)]


def passing_gate():
    return {
        "gate_version": "experiment_a_to_b_v1", "negative_variants": 2, "total_variants": 3,
        "mean_interaction": -0.125, "experiment_b_dispatch": True, "validation_status": "pass",
        "validation_sha256": "1" * 64, "experiment_a_results_sha256": "2" * 64,
        "frozen_variants_sha256": "3" * 64,
    }


def test_manifest_exact_matrix_and_gate_binding():
    rows = experiment_b_manifest(variants(), PROVENANCE, "f" * 64, "e" * 64)
    assert len(rows) == 64 and len({row["run_id"] for row in rows}) == 64
    assert Counter(row["scene"] for row in rows) == {"ood": 48, "id": 16}
    assert {int(row["seed"]) for row in rows} == set(SEEDS)
    assert {int(row["added_delay_ms"]) for row in rows} == set(DELAYS)
    assert {int(row["configured_n_action_steps"]) for row in rows} == {HORIZON}
    assert {row["analysis_status"] for row in rows} == {ANALYSIS_STATUS}
    assert {row["experiment_a_dispatch_gate_sha256"] for row in rows} == {"e" * 64}


def test_deterministic_variant_selection():
    entries = [
        {"id": 14, "name": BASE_TASK_NAME + "_layout_14", "category": "Objects Layout", "difficulty_level": 3},
        {"id": 13, "name": BASE_TASK_NAME + "_layout_13", "category": "Objects Layout", "difficulty_level": 2},
        {"id": 12, "name": BASE_TASK_NAME + "_layout_12", "category": "Objects Layout", "difficulty_level": 2},
        {"id": 11, "name": BASE_TASK_NAME + "_layout_11", "category": "Objects Layout", "difficulty_level": 1},
    ]
    selected = select_variant_entries(entries, [entry["name"] for entry in entries])
    assert [row["classification_id"] for row in selected] == ["12", "13", "11"]


def test_dispatch_gate_fails_closed(tmp_path):
    gate_path = tmp_path / "gate.json"
    gate = passing_gate(); gate["experiment_b_dispatch"] = False
    gate_path.write_text(json.dumps(gate))
    with pytest.raises(ValueError):
        validate_experiment_a_gate(gate_path)
    gate_path.write_text(json.dumps(passing_gate()))
    assert len(validate_experiment_a_gate(gate_path)) == 64


def test_runner_requires_gate_and_explicit_zero_index():
    source = (Path(__file__).parents[1] / "scripts/run_stage3.py").read_text()
    assert '"experiment_b"' in source
    assert "Experiment B requires --dispatch-gate" in source
    assert "episode_index=0" in source
    assert 'args.stage_label not in ("experiment_a","experiment_b")' in source


def test_interaction_uses_seed_paired_four_cells_and_shared_id():
    variant_name = BASE_TASK_NAME + "_layout_test"
    rows = []
    # Seed 30: OOD falls by one while ID is unchanged => I=-1.
    # Seed 31: OOD is unchanged while ID falls by one => I=+1.
    outcomes = {
        30: {("id", 0): 1, ("id", 200): 1, ("ood", 0): 1, ("ood", 200): 0},
        31: {("id", 0): 1, ("id", 200): 0, ("ood", 0): 1, ("ood", 200): 1},
    }
    for seed, cells in outcomes.items():
        for (scene, delay), success in cells.items():
            rows.append({"scene_condition": scene, "variant_name": BASE_TASK_NAME if scene == "id" else variant_name, "added_delay_ms": delay, "seed": seed, "success": success})
    assert paired_interaction_values(rows, variant_name, seeds=(30, 31)) == [-1, 1]
