"""Frozen Experiment B cross-task object-layout generalization."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Mapping, Sequence

from async_vla_benchmark.benchmark.stage3 import Stage3Plan

TASK_KEY = "additional_multistage_task"
SUITE = "libero_10"
BASE_TASK_ID = 0
BASE_TASK_NAME = "LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket"
TASK_DEMAND_TYPE = "multi_stage_sequential"
SEEDS = tuple(range(30, 38))
DELAYS = (0, 200)
HORIZON = 25
ANALYSIS_STATUS = "conditional_cross_task_generalization"


def paired_interaction_values(rows, variant_name, seeds=SEEDS):
    """Return one four-cell difference-in-differences value per rollout seed."""
    def outcome(scene, target_name, delay, seed):
        matches = [row for row in rows if row["scene_condition"] == scene and row["variant_name"] == target_name and int(row["added_delay_ms"]) == delay and int(row["seed"]) == seed]
        if len(matches) != 1:
            raise ValueError(f"expected one {scene}/{target_name}/{delay}/s{seed} row, got {len(matches)}")
        return int(matches[0]["success"])
    return [
        (outcome("ood", variant_name, 200, seed) - outcome("ood", variant_name, 0, seed))
        - (outcome("id", BASE_TASK_NAME, 200, seed) - outcome("id", BASE_TASK_NAME, 0, seed))
        for seed in seeds
    ]


def validate_experiment_a_gate(path: Path) -> str:
    """Require the exact frozen Experiment-A-to-B dispatch decision."""
    gate = json.loads(path.read_text())
    required = {
        "gate_version": "experiment_a_to_b_v1",
        "total_variants": 3,
        "experiment_b_dispatch": True,
        "validation_status": "pass",
    }
    if any(gate.get(key) != value for key, value in required.items()):
        raise ValueError("Experiment A dispatch gate is absent, failed, or incompatible")
    if int(gate.get("negative_variants", -1)) < 2 or float(gate.get("mean_interaction", 0.0)) >= 0:
        raise ValueError("Experiment A did not satisfy the frozen directional gate")
    for field in ("validation_sha256", "experiment_a_results_sha256", "frozen_variants_sha256"):
        value = str(gate.get(field, ""))
        if len(value) != 64:
            raise ValueError(f"Experiment A gate lacks valid {field}")
        try: int(value, 16)
        except ValueError as exc: raise ValueError(f"Experiment A gate has non-hex {field}") from exc
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_variant_entries(entries, api_names):
    """Apply the frozen nearest-L2/lowest-classification-ID rule."""
    candidates = [
        entry for entry in entries
        if str(entry["name"]).startswith(BASE_TASK_NAME)
        and str(entry["category"]) == "Objects Layout"
    ]
    try:
        candidates.sort(key=lambda entry: (abs(int(entry["difficulty_level"]) - 2), int(entry["id"])))
    except (TypeError, ValueError) as exc:
        raise ValueError("Experiment B matched an unscored object-layout candidate") from exc
    if len(candidates) < 3:
        raise ValueError(f"only {len(candidates)} eligible variants; exactly 3 required")
    names = list(api_names)
    rows = []
    for entry in candidates[:3]:
        name = str(entry["name"])
        if names.count(name) != 1:
            raise ValueError(f"expected one exact API task-name match for {name!r}")
        api_index = names.index(name)
        rows.append({
            "task_key": TASK_KEY, "suite": SUITE, "base_task_id": str(BASE_TASK_ID),
            "base_task_name": BASE_TASK_NAME, "task_demand_type": TASK_DEMAND_TYPE,
            "perturbation_key": "object_layout", "official_category": "Objects Layout",
            "mechanism_group": "trajectory_adaptation", "classification_id": str(int(entry["id"])),
            "api_task_index": str(api_index), "difficulty_level": str(int(entry["difficulty_level"])),
            "variant_name": name,
        })
    validate_frozen_variants(rows)
    return rows


def validate_frozen_variants(variants: Sequence[Mapping[str, str]]) -> None:
    if len(variants) != 3 or len({row["classification_id"] for row in variants}) != 3:
        raise ValueError("Experiment B requires exactly three unique frozen variants")
    expected = {
        "task_key": TASK_KEY, "suite": SUITE, "base_task_id": str(BASE_TASK_ID),
        "base_task_name": BASE_TASK_NAME, "task_demand_type": TASK_DEMAND_TYPE,
        "perturbation_key": "object_layout", "official_category": "Objects Layout",
        "mechanism_group": "trajectory_adaptation",
    }
    for row in variants:
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError(f"invalid Experiment B frozen variant row: {row}")
        if not row["variant_name"].startswith(BASE_TASK_NAME):
            raise ValueError("variant does not match the frozen Experiment B base task")
        int(row["classification_id"]); int(row["api_task_index"]); int(row["difficulty_level"])


def _plan(provenance, variant, scene, delay, seed, frozen_hash, gate_hash):
    if scene == "id":
        api, name, classification, difficulty = BASE_TASK_ID, BASE_TASK_NAME, "", ""
        perturbation, category, mechanism, variant_token = "id", "ID", "id", "id"
    else:
        api, name = int(variant["api_task_index"]), variant["variant_name"]
        classification, difficulty = variant["classification_id"], variant["difficulty_level"]
        perturbation, category, mechanism = "object_layout", "Objects Layout", "trajectory_adaptation"
        variant_token = f"c{classification}"
    run_id = f"experiment_b__{TASK_KEY}__{scene}__{variant_token}__rtc__h25__d{delay}__s{seed}"
    plan = asdict(Stage3Plan(
        run_id=run_id, stage="experiment_b", analysis_status=ANALYSIS_STATUS,
        git_sha=provenance["git_sha"], lerobot_git_sha=provenance["lerobot_git_sha"],
        libero_plus_git_sha=provenance["libero_plus_git_sha"], model_revision=provenance["model_revision"],
        checkpoint_id="lerobot/pi05_libero_finetuned@" + provenance["model_revision"],
        runner_commit=provenance["git_sha"],
        environment_version=provenance["lerobot_git_sha"] if scene == "id" else provenance["libero_plus_git_sha"],
        task_key=TASK_KEY, task_group=TASK_DEMAND_TYPE, suite=SUITE,
        base_task_id=BASE_TASK_ID, base_task_name=BASE_TASK_NAME,
        task_id=api, task_name=name, api_task_index=api, variant_name=name,
        classification_id=str(classification), difficulty_level=str(difficulty),
        perturbation_key=perturbation, official_category=category, mechanism_group=mechanism,
        scene=scene, scene_condition=scene, execution_method="rtc",
        configured_n_action_steps=HORIZON, rtc_execution_horizon=HORIZON,
        request_threshold_actions=HORIZON, added_delay_ms=delay,
        delay_condition="native" if delay == 0 else "plus_200ms", seed=seed,
        initialization_index_or_id="libero_episode_index:0",
        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
        output_path=f"episodes/{run_id}.json",
    ))
    plan.update({
        "stage_or_experiment_label": "experiment_b", "requested_initialization_index": 0,
        "resolved_initialization_index_or_id": "PENDING_PREFLIGHT_RESOLUTION",
        "frozen_variant_csv_sha256": frozen_hash, "experiment_a_dispatch_gate_sha256": gate_hash,
    })
    return plan


def experiment_b_manifest(variants, provenance, frozen_hash, gate_hash):
    validate_frozen_variants(variants)
    rows = []
    for delay in DELAYS:
        for seed in SEEDS:
            rows.append(_plan(provenance, None, "id", delay, seed, frozen_hash, gate_hash))
    for variant in variants:
        for delay in DELAYS:
            for seed in SEEDS:
                rows.append(_plan(provenance, variant, "ood", delay, seed, frozen_hash, gate_hash))
    validate_manifest(rows, variants, frozen_hash, gate_hash)
    return rows


def validate_manifest(rows, variants, frozen_hash, gate_hash):
    if len(rows) != 64 or len({row["run_id"] for row in rows}) != 64:
        raise ValueError("Experiment B manifest must contain 64 unique episodes")
    if sum(row["scene"] == "id" for row in rows) != 16 or sum(row["scene"] == "ood" for row in rows) != 48:
        raise ValueError("Experiment B accounting must be 16 ID + 48 OOD")
    if {int(row["seed"]) for row in rows} != set(SEEDS) or {int(row["added_delay_ms"]) for row in rows} != set(DELAYS):
        raise ValueError("Experiment B seeds or delays changed")
    if {int(row["configured_n_action_steps"]) for row in rows} != {HORIZON} or {row["execution_method"] for row in rows} != {"rtc"}:
        raise ValueError("Experiment B method/horizon changed")
    if {row["frozen_variant_csv_sha256"] for row in rows} != {frozen_hash}:
        raise ValueError("manifest does not consume one frozen variant artifact")
    if {row["experiment_a_dispatch_gate_sha256"] for row in rows} != {gate_hash}:
        raise ValueError("manifest does not consume the passing Experiment A gate")
    expected = {(v["classification_id"], v["api_task_index"], v["difficulty_level"], v["variant_name"]) for v in variants}
    actual = {(r["classification_id"], str(r["api_task_index"]), r["difficulty_level"], r["variant_name"]) for r in rows if r["scene"] == "ood"}
    if actual != expected:
        raise ValueError("manifest variant identities differ from frozen CSV")
    if any(str(row.get("requested_initialization_index")) != "0" for row in rows):
        raise ValueError("Experiment B must request initialization zero")
