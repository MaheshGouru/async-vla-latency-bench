"""Frozen, conditional Stage 4 matched RTC/VLASH design."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from async_vla_benchmark.benchmark.stage3 import OOD_VARIANTS, TASKS

SEEDS = (22, 23, 24, 25, 26)
METHODS = ("rtc", "vlash")
ADDED_DELAYS_MS = (0, 200)
N_ACTION_STEPS = 25
ANALYSIS_STATUS = "conditional_method_validation"

# Only prespecified Stage 3 candidates are eligible. Sensor noise is deliberately
# absent and cannot be promoted to fill the two-candidate quota.
ELIGIBLE_VARIANTS = {
    value["perturbation_key"]: dict(value)
    for value in OOD_VARIANTS
    if value["analysis_status"] == "prespecified_confirmatory"
}


@dataclass(frozen=True)
class Stage4Plan:
    run_id: str
    stage: str
    analysis_status: str
    candidate_key: str
    git_sha: str
    lerobot_git_sha: str
    libero_plus_git_sha: str
    model_revision: str
    checkpoint_id: str
    runner_commit: str
    vlash_repository: str
    vlash_revision: str
    vlash_checkpoint_id: str
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
    configured_n_action_steps: int
    added_delay_ms: int
    delay_condition: str
    seed: int
    initialization_index_or_id: str
    initial_state_fingerprint: str
    initial_state_fingerprint_method: str
    output_path: str
    status: str = "pending"


def validate_candidates(candidates: Sequence[Mapping[str, str]]) -> None:
    if not 1 <= len(candidates) <= 2:
        raise ValueError("Stage 4 requires one or two reviewed candidates")
    keys = [row["perturbation_key"] for row in candidates]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate Stage 4 candidate")
    for row in candidates:
        key = row["perturbation_key"]
        expected = ELIGIBLE_VARIANTS.get(key)
        if expected is None:
            raise ValueError(f"ineligible Stage 4 candidate: {key}")
        for field in ("task_key", "classification_id", "api_task_index", "variant_name", "difficulty_level"):
            if str(row.get(field, "")) != str(expected[field]):
                raise ValueError(f"{key}: frozen {field} changed")
        if row.get("stage3_analysis_status") != "prespecified_confirmatory":
            raise ValueError(f"{key}: only prespecified Stage 3 candidates are eligible")
        if row.get("selection_frozen_before_vlash_outcomes") != "True":
            raise ValueError(f"{key}: selection was not frozen before VLASH outcomes")


def _row(provenance, task_key, scene, variant, method, delay, seed):
    task = TASKS[task_key]
    if scene == "id":
        api_index, name = task["task_id"], task["base_name"]
        perturbation, category, mechanism = "id", "ID", "id"
        classification_id = difficulty = ""
        candidate_key = f"shared_id:{task_key}"
    else:
        api_index, name = int(variant["api_task_index"]), variant["variant_name"]
        perturbation = variant["perturbation_key"]
        category, mechanism = variant["official_category"], variant["mechanism_group"]
        classification_id, difficulty = str(variant["classification_id"]), str(variant["difficulty_level"])
        candidate_key = f"{task_key}:{perturbation}"
    run_id = f"stage4__{task_key}__{scene}__{perturbation}__{method}__h25__d{delay}__s{seed}"
    return Stage4Plan(
        run_id=run_id, stage="stage4", analysis_status=ANALYSIS_STATUS,
        candidate_key=candidate_key, git_sha=provenance["git_sha"],
        lerobot_git_sha=provenance["lerobot_git_sha"],
        libero_plus_git_sha=provenance["libero_plus_git_sha"],
        model_revision=provenance["model_revision"],
        checkpoint_id="lerobot/pi05_libero_finetuned@" + provenance["model_revision"],
        runner_commit=provenance["git_sha"],
        vlash_repository=provenance["vlash_repository"],
        vlash_revision=provenance["vlash_revision"],
        vlash_checkpoint_id=provenance["vlash_checkpoint_id"],
        task_key=task_key, task_group=task["task_group"], suite=task["suite"],
        base_task_id=task["task_id"], base_task_name=task["base_name"],
        task_id=api_index, task_name=name, api_task_index=api_index,
        variant_name=name, classification_id=classification_id,
        difficulty_level=difficulty, perturbation_key=perturbation,
        official_category=category, mechanism_group=mechanism,
        scene=scene, scene_condition=scene, execution_method=method,
        configured_n_action_steps=N_ACTION_STEPS, added_delay_ms=delay,
        delay_condition="native" if delay == 0 else "plus_200ms", seed=seed,
        initialization_index_or_id="libero_episode_index:0",
        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
        output_path=f"episodes/{run_id}.json",
    )


def stage4_manifest(candidates: Sequence[Mapping[str, str]], provenance: Mapping[str, str]) -> list[Stage4Plan]:
    validate_candidates(candidates)
    variants = [ELIGIBLE_VARIANTS[row["perturbation_key"]] for row in candidates]
    rows = []
    # Physical ID controls are unique per base task and shared by all candidates
    # on that task. Candidate-level analysis joins them by task_key.
    for task_key in sorted({value["task_key"] for value in variants}):
        for method in METHODS:
            for delay in ADDED_DELAYS_MS:
                for seed in SEEDS:
                    rows.append(_row(provenance, task_key, "id", None, method, delay, seed))
    for variant in variants:
        for method in METHODS:
            for delay in ADDED_DELAYS_MS:
                for seed in SEEDS:
                    rows.append(_row(provenance, variant["task_key"], "ood", variant, method, delay, seed))
    validate_manifest(rows, candidates)
    return rows


def validate_manifest(rows: Sequence[Stage4Plan], candidates: Sequence[Mapping[str, str]]) -> None:
    tasks = {row["task_key"] for row in candidates}
    expected = 20 * (len(candidates) + len(tasks))
    if len(rows) != expected or len({row.run_id for row in rows}) != expected:
        raise ValueError(f"Stage 4 requires {expected} unique physical episodes")
    if {row.seed for row in rows} != set(SEEDS): raise ValueError("wrong Stage 4 seeds")
    if {row.execution_method for row in rows} != set(METHODS): raise ValueError("wrong Stage 4 methods")
    if {row.added_delay_ms for row in rows} != set(ADDED_DELAYS_MS): raise ValueError("wrong Stage 4 delays")
    if any(row.configured_n_action_steps != N_ACTION_STEPS for row in rows): raise ValueError("Stage 4 must use h=25")
    keys={(r.scene,r.task_key,r.variant_name,r.execution_method,r.added_delay_ms,r.seed) for r in rows}
    if len(keys) != expected: raise ValueError("duplicate Stage 4 physical condition")


def as_rows(rows: Sequence[Stage4Plan]) -> list[dict]:
    return [asdict(row) for row in rows]
