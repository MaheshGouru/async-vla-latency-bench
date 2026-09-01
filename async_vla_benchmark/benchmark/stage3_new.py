"""Frozen Stage 3 New — high-power replication of the Stage 3 / Stage 3B matrix.

64 completely fresh rollout seeds (46-109) per unique cell.
Seeds 14-21 (old Stage 3/3B block) must never appear here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

HORIZONS = (20, 25, 30)
ADDED_DELAYS_MS = (0, 200)
SEEDS = tuple(range(46, 110))  # 64 fresh seeds
METHOD = "rtc"
STAGE_LABEL = "stage3_new"

_OLD_SEEDS = frozenset(range(14, 22))

_EXPECTED_OOD   = 6 * 3 * 2 * 64   # 2,304
_EXPECTED_ID    = 3 * 3 * 2 * 64   # 1,152
_EXPECTED_TOTAL = _EXPECTED_OOD + _EXPECTED_ID  # 3,456

TASKS = {
    "spatial_transport": {
        "suite": "libero_spatial", "task_id": 2,
        "base_name": "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate",
        "task_group": "single_stage_transport",
    },
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

# 6 candidates: 4 from Stage 3 + 2 unique from Stage 3B.
# long_stove_moka x object_layout overlaps both stages and is executed once.
CANDIDATES = (
    {
        "candidate_key": "long_stove_object_layout",
        "task_key": "long_stove_moka",
        "perturbation_key": "object_layout",
        "official_category": "Objects Layout",
        "mechanism_group": "trajectory_adaptation",
        "classification_id": 1941, "api_task_index": 1940,
        "variant_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25",
        "difficulty_level": 2, "analysis_status": "prespecified_confirmatory",
        "candidate_original_status": "stage3_prespecified",
    },
    {
        "candidate_key": "goal_robot_initial_state",
        "task_key": "goal_drawer",
        "perturbation_key": "robot_initial_state",
        "official_category": "Robot Initial States",
        "mechanism_group": "trajectory_adaptation",
        "classification_id": 285, "api_task_index": 284,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_71",
        "difficulty_level": 2, "analysis_status": "prespecified_confirmatory",
        "candidate_original_status": "stage3_prespecified",
    },
    {
        "candidate_key": "goal_light_conditions",
        "task_key": "goal_drawer",
        "perturbation_key": "light_conditions",
        "official_category": "Light Conditions",
        "mechanism_group": "appearance_invariance",
        "classification_id": 2313, "api_task_index": 2312,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_light_1",
        "difficulty_level": 2, "analysis_status": "prespecified_confirmatory",
        "candidate_original_status": "stage3_prespecified",
    },
    {
        "candidate_key": "goal_sensor_noise_posthoc",
        "task_key": "goal_drawer",
        "perturbation_key": "sensor_noise",
        "official_category": "Sensor Noise",
        "mechanism_group": "perceptual_localization",
        "classification_id": 1509, "api_task_index": 1508,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_0_noise_1",
        "difficulty_level": 2, "analysis_status": "posthoc_replication",
        "candidate_original_status": "stage3_posthoc",
    },
    {
        "candidate_key": "spatial_object_layout",
        "task_key": "spatial_transport",
        "perturbation_key": "object_layout",
        "official_category": "Objects Layout",
        "mechanism_group": "trajectory_adaptation",
        "classification_id": 1773, "api_task_index": 1772,
        "variant_name": "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15",
        "difficulty_level": 3, "analysis_status": "targeted_post_stage3",
        "candidate_original_status": "stage3b_targeted",
    },
    {
        "candidate_key": "goal_object_layout",
        "task_key": "goal_drawer",
        "perturbation_key": "object_layout",
        "official_category": "Objects Layout",
        "mechanism_group": "trajectory_adaptation",
        "classification_id": 1891, "api_task_index": 1890,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_add_13",
        "difficulty_level": 2, "analysis_status": "targeted_post_stage3",
        "candidate_original_status": "stage3b_targeted",
    },
)


@dataclass(frozen=True)
class Stage3NewPlan:
    run_id: str
    stage: str
    candidate_key: str
    candidate_original_status: str
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
    requested_initialization_index: str
    output_path: str
    status: str = "pending"
    invalid_reason: str = ""


def _row(provenance: Mapping[str, str], task_key: str, scene: str,
         candidate: dict | None, horizon: int, delay: int, seed: int) -> Stage3NewPlan:
    task = TASKS[task_key]
    if scene == "id":
        api_index    = task["task_id"]
        variant_name = task["base_name"]
        perturbation = "id"
        category     = "ID"
        mechanism    = "id"
        cls_id       = ""
        difficulty   = ""
        a_status     = "shared_id_control"
        cand_key     = "shared_id"
        cand_orig    = "shared_id_control"
    else:
        api_index    = candidate["api_task_index"]
        variant_name = candidate["variant_name"]
        perturbation = candidate["perturbation_key"]
        category     = candidate["official_category"]
        mechanism    = candidate["mechanism_group"]
        cls_id       = str(candidate["classification_id"])
        difficulty   = str(candidate["difficulty_level"])
        a_status     = candidate["analysis_status"]
        cand_key     = candidate["candidate_key"]
        cand_orig    = candidate["candidate_original_status"]

    run_id = (
        f"stage3_new__{task_key}__{scene}__{perturbation}"
        f"__rtc__h{horizon}__d{delay}__s{seed}"
    )
    return Stage3NewPlan(
        run_id=run_id, stage=STAGE_LABEL,
        candidate_key=cand_key, candidate_original_status=cand_orig,
        analysis_status=a_status,
        git_sha=provenance["git_sha"],
        lerobot_git_sha=provenance["lerobot_git_sha"],
        libero_plus_git_sha=provenance["libero_plus_git_sha"],
        model_revision=provenance["model_revision"],
        checkpoint_id="lerobot/pi05_libero_finetuned@" + provenance["model_revision"],
        runner_commit=provenance["git_sha"],
        environment_version=(
            provenance["lerobot_git_sha"] if scene == "id"
            else provenance["libero_plus_git_sha"]
        ),
        task_key=task_key, task_group=task["task_group"],
        suite=task["suite"], base_task_id=task["task_id"],
        base_task_name=task["base_name"], task_id=api_index,
        task_name=variant_name, api_task_index=api_index,
        variant_name=variant_name, classification_id=cls_id,
        difficulty_level=difficulty, perturbation_key=perturbation,
        official_category=category, mechanism_group=mechanism,
        scene=scene, scene_condition=scene, execution_method=METHOD,
        configured_n_action_steps=horizon, rtc_execution_horizon=horizon,
        request_threshold_actions=horizon, added_delay_ms=delay,
        delay_condition="native" if delay == 0 else "plus_200ms",
        seed=seed,
        initialization_index_or_id="libero_episode_index:0",
        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
        requested_initialization_index="0",
        output_path=f"episodes/{run_id}.json",
    )


def stage3_new_manifest(provenance: Mapping[str, str],
                        smoke_seed: int | None = None,
                        smoke_horizon: int | None = None) -> list[Stage3NewPlan]:
    seeds    = (smoke_seed,)    if smoke_seed    is not None else SEEDS
    horizons = (smoke_horizon,) if smoke_horizon is not None else HORIZONS
    rows: list[Stage3NewPlan] = []
    for task_key in TASKS:
        for horizon in horizons:
            for delay in ADDED_DELAYS_MS:
                for seed in seeds:
                    rows.append(_row(provenance, task_key, "id", None, horizon, delay, seed))
    for candidate in CANDIDATES:
        for horizon in horizons:
            for delay in ADDED_DELAYS_MS:
                for seed in seeds:
                    rows.append(_row(provenance, candidate["task_key"], "ood",
                                     candidate, horizon, delay, seed))
    if smoke_seed is None:
        validate_manifest(rows)
    return rows


def validate_manifest(rows: Sequence[Stage3NewPlan]) -> None:
    if len(rows) != _EXPECTED_TOTAL:
        raise ValueError(
            f"Stage 3 New manifest must contain {_EXPECTED_TOTAL} rows; got {len(rows)}")
    if len({r.run_id for r in rows}) != _EXPECTED_TOTAL:
        raise ValueError("Stage 3 New manifest contains duplicate run_ids")
    seed_set = {r.seed for r in rows}
    if seed_set != set(SEEDS):
        raise ValueError(f"Seeds must be exactly {min(SEEDS)}..{max(SEEDS)}")
    if seed_set & _OLD_SEEDS:
        raise ValueError("Manifest contains forbidden old Stage 3/3B seeds (14-21)")
    if {r.configured_n_action_steps for r in rows} != set(HORIZONS):
        raise ValueError("Wrong Stage 3 New horizons")
    if {r.added_delay_ms for r in rows} != set(ADDED_DELAYS_MS):
        raise ValueError("Wrong Stage 3 New delays")
    if any(r.execution_method != METHOD for r in rows):
        raise ValueError("Stage 3 New is RTC-only")
    id_rows  = [r for r in rows if r.scene == "id"]
    ood_rows = [r for r in rows if r.scene == "ood"]
    if len(id_rows) != _EXPECTED_ID:
        raise ValueError(f"Expected {_EXPECTED_ID} ID rows; got {len(id_rows)}")
    if len(ood_rows) != _EXPECTED_OOD:
        raise ValueError(f"Expected {_EXPECTED_OOD} OOD rows; got {len(ood_rows)}")
    expected_cands = {
        (str(c["classification_id"]), c["api_task_index"], c["variant_name"],
         str(c["difficulty_level"]))
        for c in CANDIDATES
    }
    actual_cands = {
        (r.classification_id, r.api_task_index, r.variant_name, r.difficulty_level)
        for r in ood_rows
    }
    if actual_cands != expected_cands:
        raise ValueError("Frozen candidate variant identities changed")
    condition_keys = {
        (r.scene, r.task_key, r.variant_name,
         r.configured_n_action_steps, r.added_delay_ms, r.seed)
        for r in rows
    }
    if len(condition_keys) != _EXPECTED_TOTAL:
        raise ValueError("Duplicate scene/task/variant/horizon/delay/seed conditions")


def as_rows(rows: Sequence[Stage3NewPlan]) -> list[dict]:
    return [asdict(r) for r in rows]
