"""Frozen Stage 5 OpenVLA-OFT coverage-calibration and conditional second-policy replication."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .stage4 import (
    CHECKPOINT_ID, CHECKPOINT_REVISION, DELAYS_MS, EXECUTION_METHOD, NATIVE_CHUNK_SIZE,
    OPENVLA_OFT_COMMIT, POLICY_FAMILY, TASKS,
)

SEEDS_5A = tuple(range(46, 51))
SEEDS_5B = tuple(range(51, 59))
CONTROL_PERIOD_MS = 50
CONTROL_RATE_HZ = 20
PREFERRED_COVERAGES = (8, 12, 16, 20, 25)
ANALYSIS_STATUS_5A = "posthoc_sensitivity"
ANALYSIS_STATUS_5B = "prespecified_second_policy_diagnostic"


def _coverage_hash(coverages: Sequence[int]) -> str:
    payload = json.dumps(sorted(coverages), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Stage5APlan:
    run_id: str
    stage: str
    stage_or_experiment_label: str
    analysis_status: str
    policy_family: str
    checkpoint_id: str
    checkpoint_revision: str
    openvla_oft_git_sha: str
    git_sha: str
    libero_plus_git_sha: str
    runner_commit: str
    task_key: str
    task_group: str
    suite: str
    base_task_id: int
    base_task_name: str
    task_id: int
    task_name: str
    api_task_index: int
    variant_name: str
    classification_id: str
    difficulty_level: str
    perturbation_key: str
    official_category: str
    mechanism_group: str
    scene: str
    scene_condition: str
    execution_method: str
    native_chunk_size: int
    model_native_output_horizon: int
    configured_action_coverage: int
    coverage_is_single_inference_native: bool
    request_threshold_actions: int
    added_delay_ms: int
    delay_condition: str
    seed: int
    requested_initialization_index: int
    resolved_initialization_index_or_id: str
    initialization_index_or_id: str
    initial_state_fingerprint: str
    initial_state_fingerprint_method: str
    output_path: str
    status: str = "pending"


@dataclass(frozen=True)
class Stage5BPlan:
    run_id: str
    stage: str
    stage_or_experiment_label: str
    analysis_status: str
    policy_family: str
    checkpoint_id: str
    checkpoint_revision: str
    openvla_oft_git_sha: str
    git_sha: str
    libero_plus_git_sha: str
    runner_commit: str
    task_key: str
    task_group: str
    suite: str
    base_task_id: int
    base_task_name: str
    task_id: int
    task_name: str
    api_task_index: int
    variant_name: str
    classification_id: str
    difficulty_level: str
    perturbation_key: str
    official_category: str
    mechanism_group: str
    scene: str
    scene_condition: str
    execution_method: str
    native_chunk_size: int
    model_native_output_horizon: int
    configured_action_coverage: int
    coverage_is_single_inference_native: bool
    request_threshold_actions: int
    added_delay_ms: int
    delay_condition: str
    seed: int
    requested_initialization_index: int
    resolved_initialization_index_or_id: str
    initialization_index_or_id: str
    initial_state_fingerprint: str
    initial_state_fingerprint_method: str
    output_path: str
    status: str = "pending"


def _plan_5a(provenance: Mapping[str, str], task_key: str, coverage: int, delay: int, seed: int) -> Stage5APlan:
    task = TASKS[task_key]
    api_index, name = task["base_task_id"], task["base_task_name"]
    coverage_is_native = coverage == NATIVE_CHUNK_SIZE
    run_id = (
        f"stage5a__{task_key}__id__openvla_oft__naive_async__"
        f"c{coverage}__d{delay}__s{seed}"
    )
    return Stage5APlan(
        run_id=run_id,
        stage="stage5a_coverage_calibration",
        stage_or_experiment_label="stage5a_coverage_calibration",
        analysis_status=ANALYSIS_STATUS_5A,
        policy_family=POLICY_FAMILY,
        checkpoint_id=CHECKPOINT_ID,
        checkpoint_revision=CHECKPOINT_REVISION,
        openvla_oft_git_sha=OPENVLA_OFT_COMMIT,
        git_sha=provenance["git_sha"],
        libero_plus_git_sha=provenance["libero_plus_git_sha"],
        runner_commit=provenance["git_sha"],
        task_key=task_key,
        task_group=task["task_group"],
        suite=task["suite"],
        base_task_id=task["base_task_id"],
        base_task_name=task["base_task_name"],
        task_id=api_index,
        task_name=name,
        api_task_index=api_index,
        variant_name=name,
        classification_id="",
        difficulty_level="",
        perturbation_key="id",
        official_category="ID",
        mechanism_group="id",
        scene="id",
        scene_condition="id",
        execution_method=EXECUTION_METHOD,
        native_chunk_size=NATIVE_CHUNK_SIZE,
        model_native_output_horizon=NATIVE_CHUNK_SIZE,
        configured_action_coverage=coverage,
        coverage_is_single_inference_native=coverage_is_native,
        request_threshold_actions=math.ceil(coverage / 2),
        added_delay_ms=delay,
        delay_condition="native" if delay == 0 else "plus_200ms",
        seed=seed,
        requested_initialization_index=0,
        resolved_initialization_index_or_id="PENDING_PREFLIGHT_RESOLUTION",
        initialization_index_or_id="libero_episode_index:0",
        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
        output_path=f"episodes/{run_id}.json",
    )


def _plan_5b(provenance: Mapping[str, str], task_key: str, scene: str, coverage: int, delay: int, seed: int) -> Stage5BPlan:
    task = TASKS[task_key]
    if scene == "id":
        api_index, name = task["base_task_id"], task["base_task_name"]
        classification_id = difficulty = ""
        perturbation, category, mechanism, token = "id", "ID", "id", "id"
    else:
        api_index, name = task["api_task_index"], task["variant_name"]
        classification_id, difficulty = task["classification_id"], task["difficulty_level"]
        perturbation, category, mechanism, token = "object_layout", "Objects Layout", "trajectory_adaptation", f"c{classification_id}"
    run_id = (
        f"stage5b__{task_key}__{scene}__{token}__openvla_oft__naive_async__"
        f"c{coverage}__d{delay}__s{seed}"
    )
    return Stage5BPlan(
        run_id=run_id,
        stage="stage5b_final_replication",
        stage_or_experiment_label="stage5b_final_replication",
        analysis_status=ANALYSIS_STATUS_5B,
        policy_family=POLICY_FAMILY,
        checkpoint_id=CHECKPOINT_ID,
        checkpoint_revision=CHECKPOINT_REVISION,
        openvla_oft_git_sha=OPENVLA_OFT_COMMIT,
        git_sha=provenance["git_sha"],
        libero_plus_git_sha=provenance["libero_plus_git_sha"],
        runner_commit=provenance["git_sha"],
        task_key=task_key,
        task_group=task["task_group"],
        suite=task["suite"],
        base_task_id=task["base_task_id"],
        base_task_name=task["base_task_name"],
        task_id=api_index,
        task_name=name,
        api_task_index=api_index,
        variant_name=name,
        classification_id=classification_id,
        difficulty_level=difficulty,
        perturbation_key=perturbation,
        official_category=category,
        mechanism_group=mechanism,
        scene=scene,
        scene_condition=scene,
        execution_method=EXECUTION_METHOD,
        native_chunk_size=NATIVE_CHUNK_SIZE,
        model_native_output_horizon=NATIVE_CHUNK_SIZE,
        configured_action_coverage=coverage,
        coverage_is_single_inference_native=True,
        request_threshold_actions=math.ceil(coverage / 2),
        added_delay_ms=delay,
        delay_condition="native" if delay == 0 else "plus_200ms",
        seed=seed,
        requested_initialization_index=0,
        resolved_initialization_index_or_id="PENDING_PREFLIGHT_RESOLUTION",
        initialization_index_or_id="libero_episode_index:0",
        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
        output_path=f"episodes/{run_id}.json",
    )


def stage5a_manifest(provenance: Mapping[str, str], coverages: Sequence[int] = PREFERRED_COVERAGES) -> list[Stage5APlan]:
    rows = [
        _plan_5a(provenance, task, c, delay, seed)
        for task in TASKS
        for c in coverages
        for delay in DELAYS_MS
        for seed in SEEDS_5A
    ]
    validate_manifest_5a(rows)
    return rows


def stage5b_manifest(provenance: Mapping[str, str], selected_coverage: int) -> list[Stage5BPlan]:
    rows = [
        _plan_5b(provenance, task, scene, selected_coverage, delay, seed)
        for task in TASKS
        for scene in ("id", "ood")
        for delay in DELAYS_MS
        for seed in SEEDS_5B
    ]
    validate_manifest_5b(rows, selected_coverage)
    return rows


def validate_manifest_5a(rows: Sequence[Stage5APlan | Mapping[str, str]]) -> None:
    if len(rows) == 0:
        raise ValueError("Stage 5A manifest is empty; the capability audit may have closed the gate")
    if len({asdict(r)["run_id"] if hasattr(r, "__dataclass_fields__") else r["run_id"] for r in rows}) != len(rows):
        raise ValueError("Stage 5A run IDs are not unique")
    covs = set(_value(r, "configured_action_coverage") for r in rows)
    if any(c > NATIVE_CHUNK_SIZE for c in covs):
        raise ValueError("Stage 5A cannot include a coverage above the audited native output horizon")
    if _value(rows[0], "scene") != "id":
        raise ValueError("Stage 5A must use ID scenes only")
    for row in rows:
        if _value(row, "seed") not in SEEDS_5A:
            raise ValueError(f"Stage 5A seed set is frozen; got {_value(row, 'seed')}")


def validate_manifest_5b(rows: Sequence[Stage5BPlan | Mapping[str, str]], selected_coverage: int) -> None:
    if len(rows) != 64 or len({asdict(r)["run_id"] if hasattr(r, "__dataclass_fields__") else r["run_id"] for r in rows}) != 64:
        raise ValueError("Stage 5B requires exactly 64 unique physical episodes")
    if any(_value(r, "configured_action_coverage") != selected_coverage for r in rows):
        raise ValueError("Stage 5B configured coverage must be the frozen selected coverage")
    if any(int(_value(r, "seed")) not in SEEDS_5B for r in rows):
        raise ValueError("Stage 5B seeds are frozen to 51..58")
    if any(_value(r, "scene") not in {"id", "ood"} for r in rows):
        raise ValueError("Stage 5B scenes must be id/ood")


def _value(row, field):
    return getattr(row, field) if hasattr(row, field) else row[field]


def as_rows(rows: Sequence) -> list[dict]:
    return [asdict(row) for row in rows]


def paired_interaction_values(rows: Sequence[Mapping[str, str]], task_key: str) -> list[float]:
    selected = [r for r in rows if r["task_key"] == task_key]
    values = []
    for seed in SEEDS_5B:
        cell = {(r["scene_condition"], int(r["added_delay_ms"])): int(r["success"])
                for r in selected if int(r["seed"]) == seed}
        expected = {(s, d) for s in ("id", "ood") for d in DELAYS_MS}
        if set(cell) != expected:
            raise ValueError(f"incomplete paired seed cluster {task_key}/{seed}")
        values.append((cell[("ood", 200)] - cell[("ood", 0)]) - (cell[("id", 200)] - cell[("id", 0)]))
    return values
