"""Frozen Stage 3 held-out OOD confirmation design."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

HORIZONS = (20, 25, 30)
ADDED_DELAYS_MS = (0, 200)
SEEDS = (14, 15, 16, 17, 18, 19, 20, 21)
METHOD = "rtc"
PRESPECIFIED = "prespecified_confirmatory"
POSTHOC = "posthoc_replication"

TASKS = {
    "goal_drawer": {
        "suite": "libero_goal", "task_id": 0,
        "base_name": "open_the_middle_drawer_of_the_cabinet",
        "task_group": "articulated_contact_rich",
    },
    "long_stove_moka": {
        "suite": "libero_10", "task_id": 2,
        "base_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",
        "task_group": "multi_stage_sequential",
    },
}

OOD_VARIANTS = (
    {
        "task_key": "long_stove_moka", "perturbation_key": "object_layout",
        "official_category": "Objects Layout", "mechanism_group": "trajectory_adaptation",
        "classification_id": 1941, "api_task_index": 1940,
        "variant_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25",
        "difficulty_level": 2, "analysis_status": "prespecified_confirmatory",
    },
    {
        "task_key": "goal_drawer", "perturbation_key": "robot_initial_state",
        "official_category": "Robot Initial States", "mechanism_group": "trajectory_adaptation",
        "classification_id": 285, "api_task_index": 284,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_71",
        "difficulty_level": 2, "analysis_status": "prespecified_confirmatory",
    },
    {
        "task_key": "goal_drawer", "perturbation_key": "light_conditions",
        "official_category": "Light Conditions", "mechanism_group": "appearance_invariance",
        "classification_id": 2313, "api_task_index": 2312,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_light_1",
        "difficulty_level": 2, "analysis_status": "prespecified_confirmatory",
    },
    {
        "task_key": "goal_drawer", "perturbation_key": "sensor_noise",
        "official_category": "Sensor Noise", "mechanism_group": "perceptual_localization",
        "classification_id": 1509, "api_task_index": 1508,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_0_noise_1",
        "difficulty_level": 2, "analysis_status": "posthoc_replication",
    },
)


@dataclass(frozen=True)
class Stage3Plan:
    run_id: str
    stage: str
    analysis_status: str
    git_sha: str
    lerobot_git_sha: str
    libero_plus_git_sha: str
    model_revision: str
    checkpoint_id: str
    runner_commit: str
    environment_version: str
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
    rtc_execution_horizon: int
    request_threshold_actions: int
    added_delay_ms: int
    delay_condition: str
    seed: int
    initialization_index_or_id: str
    initial_state_fingerprint: str
    initial_state_fingerprint_method: str
    output_path: str
    status: str = "pending"
    invalid_reason: str = ""


def _row(provenance, task_key, scene, variant, horizon, delay, seed):
    task = TASKS[task_key]
    if scene == "id":
        api_index = task["task_id"]
        variant_name = task["base_name"]
        perturbation = "id"
        category = "ID"
        mechanism = "id"
        classification_id = ""
        difficulty = ""
        status = "prespecified_confirmatory"
    else:
        api_index = variant["api_task_index"]
        variant_name = variant["variant_name"]
        perturbation = variant["perturbation_key"]
        category = variant["official_category"]
        mechanism = variant["mechanism_group"]
        classification_id = str(variant["classification_id"])
        difficulty = str(variant["difficulty_level"])
        status = variant["analysis_status"]
    run_id = f"stage3__{task_key}__{scene}__{perturbation}__rtc__h{horizon}__d{delay}__s{seed}"
    return Stage3Plan(
        run_id=run_id, stage="stage3", analysis_status=status,
        git_sha=provenance["git_sha"], lerobot_git_sha=provenance["lerobot_git_sha"],
        libero_plus_git_sha=provenance["libero_plus_git_sha"],
        model_revision=provenance["model_revision"],
        checkpoint_id="lerobot/pi05_libero_finetuned@" + provenance["model_revision"],
        runner_commit=provenance["git_sha"],
        environment_version=(provenance["lerobot_git_sha"] if scene == "id" else provenance["libero_plus_git_sha"]),
        task_key=task_key, task_group=task["task_group"], suite=task["suite"],
        base_task_id=task["task_id"], base_task_name=task["base_name"],
        task_id=api_index, task_name=variant_name, api_task_index=api_index,
        variant_name=variant_name, classification_id=classification_id,
        difficulty_level=difficulty, perturbation_key=perturbation,
        official_category=category, mechanism_group=mechanism,
        scene=scene, scene_condition=scene, execution_method=METHOD,
        configured_n_action_steps=horizon, rtc_execution_horizon=horizon,
        request_threshold_actions=horizon, added_delay_ms=delay,
        delay_condition="native" if delay == 0 else "plus_200ms", seed=seed,
        initialization_index_or_id="libero_episode_index:0",
        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
        output_path=f"episodes/{run_id}.json",
    )


def stage3_manifest(provenance: Mapping[str, str]) -> list[Stage3Plan]:
    rows = []
    for task_key in TASKS:
        for horizon in HORIZONS:
            for delay in ADDED_DELAYS_MS:
                for seed in SEEDS:
                    rows.append(_row(provenance, task_key, "id", None, horizon, delay, seed))
    for variant in OOD_VARIANTS:
        for horizon in HORIZONS:
            for delay in ADDED_DELAYS_MS:
                for seed in SEEDS:
                    rows.append(_row(provenance, variant["task_key"], "ood", variant, horizon, delay, seed))
    validate_manifest(rows)
    return rows


def validate_manifest(rows: Sequence[Stage3Plan]) -> None:
    if len(rows) != 288 or len({row.run_id for row in rows}) != 288:
        raise ValueError("Stage 3 manifest must contain 288 unique episodes")
    if {row.configured_n_action_steps for row in rows} != set(HORIZONS): raise ValueError("wrong Stage 3 horizons")
    if {row.added_delay_ms for row in rows} != set(ADDED_DELAYS_MS): raise ValueError("wrong Stage 3 delays")
    if {row.seed for row in rows} != set(SEEDS): raise ValueError("wrong Stage 3 seeds")
    if any(row.execution_method != METHOD for row in rows): raise ValueError("Stage 3 is RTC-only")
    if sum(row.scene == "id" for row in rows) != 96 or sum(row.scene == "ood" for row in rows) != 192:
        raise ValueError("Stage 3 must contain 96 shared ID and 192 OOD episodes")
    condition_keys = {
        (row.scene, row.task_key, row.variant_name, row.configured_n_action_steps,
         row.added_delay_ms, row.seed)
        for row in rows
    }
    if len(condition_keys) != 288:
        raise ValueError("Stage 3 contains duplicate scene/task/variant/horizon/delay/seed conditions")
    if sum(row.analysis_status == PRESPECIFIED for row in rows) != 240:
        raise ValueError("Stage 3 primary analysis must contain exactly 240 unique episodes")
    if sum(row.analysis_status == POSTHOC for row in rows) != 48:
        raise ValueError("Stage 3 post-hoc sensor-noise replication must contain exactly 48 episodes")
    expected = {
        (str(v["classification_id"]), v["api_task_index"], v["variant_name"],
         str(v["difficulty_level"]), v["analysis_status"])
        for v in OOD_VARIANTS
    }
    actual = {
        (row.classification_id, row.api_task_index, row.variant_name,
         row.difficulty_level, row.analysis_status)
        for row in rows if row.scene == "ood"
    }
    if actual != expected:
        raise ValueError("Stage 3 exact frozen OOD variant identities changed")
    if any(row.rtc_execution_horizon != row.configured_n_action_steps for row in rows): raise ValueError("RTC horizon mismatch")
    if any(row.request_threshold_actions != row.configured_n_action_steps for row in rows): raise ValueError("request threshold mismatch")


def as_rows(rows: Sequence[Stage3Plan]) -> list[dict]:
    return [asdict(row) for row in rows]
