"""Frozen Experiment A within-task object-layout variant generalization."""
from __future__ import annotations
from dataclasses import asdict
from typing import Mapping, Sequence

from async_vla_benchmark.benchmark.stage3 import Stage3Plan

TASK_KEY = "long_stove_moka"
SUITE = "libero_10"
BASE_TASK_ID = 2
BASE_TASK_NAME = "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it"
TASK_DEMAND_TYPE = "multi_stage_sequential"
EXCLUDED_CLASSIFICATION_ID = 1941
EXCLUDED_VARIANT_NAME = BASE_TASK_NAME + "_add_25"
SEEDS = tuple(range(22, 30))
DELAYS = (0, 200)
HORIZON = 25
ANALYSIS_STATUS = "targeted_post_stage3b_variant_generalization"


def select_variant_entries(entries, api_names):
    """Apply the frozen scored-nearest-L2/lowest-ID rule and exact API lookup."""
    candidates=[e for e in entries if str(e["name"]).startswith(BASE_TASK_NAME)
                and str(e["category"])=="Objects Layout"
                and int(e["id"])!=EXCLUDED_CLASSIFICATION_ID
                and str(e["name"])!=EXCLUDED_VARIANT_NAME
                and e.get("difficulty_level") is not None
                and str(e.get("difficulty_level","")).strip()]
    candidates.sort(key=lambda e:(abs(int(e["difficulty_level"])-2),int(e["id"])))
    if len(candidates)<3: raise ValueError(f"only {len(candidates)} eligible scored variants; exactly 3 required")
    rows=[]; names=list(api_names)
    for entry in candidates[:3]:
        name=str(entry["name"]); api_index=names.index(name)
        if names[api_index]!=name: raise RuntimeError("exact API variant-name resolution failed")
        rows.append({"task_key":TASK_KEY,"suite":SUITE,"base_task_id":str(BASE_TASK_ID),"base_task_name":BASE_TASK_NAME,"task_demand_type":TASK_DEMAND_TYPE,"perturbation_key":"object_layout","official_category":"Objects Layout","mechanism_group":"trajectory_adaptation","classification_id":str(int(entry["id"])),"api_task_index":str(api_index),"difficulty_level":str(int(entry["difficulty_level"])),"variant_name":name})
    validate_frozen_variants(rows); return rows


def validate_frozen_variants(variants: Sequence[Mapping[str, str]]) -> None:
    if len(variants) != 3 or len({v["classification_id"] for v in variants}) != 3:
        raise ValueError("Experiment A requires exactly three unique frozen variants")
    for row in variants:
        expected = {
            "task_key": TASK_KEY, "suite": SUITE, "base_task_id": str(BASE_TASK_ID),
            "base_task_name": BASE_TASK_NAME, "task_demand_type": TASK_DEMAND_TYPE,
            "perturbation_key": "object_layout", "official_category": "Objects Layout",
            "mechanism_group": "trajectory_adaptation",
        }
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError(f"invalid Experiment A frozen variant row: {row}")
        if int(row["classification_id"]) == EXCLUDED_CLASSIFICATION_ID or row["variant_name"] == EXCLUDED_VARIANT_NAME:
            raise ValueError("previously evaluated _add_25 variant was not excluded")
        if not row["variant_name"].startswith(BASE_TASK_NAME):
            raise ValueError("variant does not match the frozen base task")
        int(row["api_task_index"]); int(row["difficulty_level"])


def _plan(provenance, variant, scene, delay, seed, frozen_hash):
    if scene == "id":
        api, name, classification, difficulty = BASE_TASK_ID, BASE_TASK_NAME, "", ""
        perturbation, category, mechanism = "id", "ID", "id"
        variant_token = "id"
    else:
        api, name = int(variant["api_task_index"]), variant["variant_name"]
        classification, difficulty = variant["classification_id"], variant["difficulty_level"]
        perturbation, category, mechanism = "object_layout", "Objects Layout", "trajectory_adaptation"
        variant_token = f"c{classification}"
    run_id = f"experiment_a__{TASK_KEY}__{scene}__{variant_token}__rtc__h25__d{delay}__s{seed}"
    plan = asdict(Stage3Plan(
        run_id=run_id, stage="experiment_a", analysis_status=ANALYSIS_STATUS,
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
    plan.update({"stage_or_experiment_label":"experiment_a",
                 "requested_initialization_index":0,
                 "resolved_initialization_index_or_id":"PENDING_PREFLIGHT_RESOLUTION",
                 "frozen_variant_csv_sha256":frozen_hash})
    return plan


def experiment_a_manifest(variants, provenance, frozen_hash):
    validate_frozen_variants(variants)
    rows=[]
    for delay in DELAYS:
        for seed in SEEDS:
            rows.append(_plan(provenance, None, "id", delay, seed, frozen_hash))
    for variant in variants:
        for delay in DELAYS:
            for seed in SEEDS:
                rows.append(_plan(provenance, variant, "ood", delay, seed, frozen_hash))
    validate_manifest(rows, variants, frozen_hash)
    return rows


def validate_manifest(rows, variants, frozen_hash):
    if len(rows) != 64 or len({r["run_id"] for r in rows}) != 64:
        raise ValueError("Experiment A manifest must contain 64 unique episodes")
    if sum(r["scene"] == "id" for r in rows) != 16 or sum(r["scene"] == "ood" for r in rows) != 48:
        raise ValueError("Experiment A accounting must be 16 ID + 48 OOD")
    if {int(r["seed"]) for r in rows} != set(SEEDS) or {int(r["added_delay_ms"]) for r in rows} != set(DELAYS):
        raise ValueError("Experiment A seeds or delays changed")
    if {int(r["configured_n_action_steps"]) for r in rows} != {HORIZON} or {r["execution_method"] for r in rows} != {"rtc"}:
        raise ValueError("Experiment A method/horizon changed")
    if {r["frozen_variant_csv_sha256"] for r in rows} != {frozen_hash}:
        raise ValueError("manifest does not consume one frozen variant artifact")
    expected={(v["classification_id"],v["api_task_index"],v["difficulty_level"],v["variant_name"]) for v in variants}
    actual={(r["classification_id"],str(r["api_task_index"]),r["difficulty_level"],r["variant_name"]) for r in rows if r["scene"]=="ood"}
    if actual != expected: raise ValueError("manifest variant identities differ from frozen CSV")
