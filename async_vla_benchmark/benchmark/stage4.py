"""Frozen Stage 4 OpenVLA-OFT second-policy diagnostic."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

SEEDS = tuple(range(38, 46))
DELAYS_MS = (0, 200)
NATIVE_CHUNK_SIZE = 8
REQUEST_THRESHOLD_ACTIONS = 4
ANALYSIS_STATUS = "prespecified_second_policy_diagnostic"
POLICY_FAMILY = "openvla_oft"
EXECUTION_METHOD = "naive_async_openvla_oft"
CHECKPOINT_ID = "moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10"
CHECKPOINT_REVISION = "13cdacd486c504e65408fc3c9e12fec9c5bf0382"
OPENVLA_OFT_REPOSITORY = "https://github.com/moojink/openvla-oft"
OPENVLA_OFT_COMMIT = "e4287e94541f459edc4feabc4e181f537cd569a8"

TASKS = {
    "spatial_transport": {
        "suite": "libero_spatial", "base_task_id": 2,
        "base_task_name": "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate",
        "task_group": "single_stage_transport",
        "classification_id": "1773", "api_task_index": 1772, "difficulty_level": "3",
        "variant_name": "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15",
    },
    "long_stove_moka": {
        "suite": "libero_10", "base_task_id": 2,
        "base_task_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",
        "task_group": "multi_stage_sequential",
        "classification_id": "1941", "api_task_index": 1940, "difficulty_level": "2",
        "variant_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25",
    },
}


@dataclass(frozen=True)
class Stage4Plan:
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
    configured_action_coverage: int
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


def _plan(provenance: Mapping[str, str], task_key: str, scene: str, delay: int, seed: int) -> Stage4Plan:
    task = TASKS[task_key]
    if scene == "id":
        api_index, name = task["base_task_id"], task["base_task_name"]
        classification_id = difficulty = ""
        perturbation, category, mechanism, token = "id", "ID", "id", "id"
    else:
        api_index, name = task["api_task_index"], task["variant_name"]
        classification_id, difficulty = task["classification_id"], task["difficulty_level"]
        perturbation, category, mechanism, token = "object_layout", "Objects Layout", "trajectory_adaptation", f"c{classification_id}"
    run_id = f"stage4__{task_key}__{scene}__{token}__openvla_oft__naive_async__d{delay}__s{seed}"
    return Stage4Plan(
        run_id=run_id, stage="stage4_second_policy", stage_or_experiment_label="stage4_second_policy",
        analysis_status=ANALYSIS_STATUS, policy_family=POLICY_FAMILY,
        checkpoint_id=CHECKPOINT_ID, checkpoint_revision=CHECKPOINT_REVISION,
        openvla_oft_git_sha=OPENVLA_OFT_COMMIT, git_sha=provenance["git_sha"],
        libero_plus_git_sha=provenance["libero_plus_git_sha"], runner_commit=provenance["git_sha"],
        task_key=task_key, task_group=task["task_group"], suite=task["suite"],
        base_task_id=task["base_task_id"], base_task_name=task["base_task_name"],
        task_id=api_index, task_name=name, api_task_index=api_index, variant_name=name,
        classification_id=classification_id, difficulty_level=difficulty,
        perturbation_key=perturbation, official_category=category, mechanism_group=mechanism,
        scene=scene, scene_condition=scene, execution_method=EXECUTION_METHOD,
        native_chunk_size=NATIVE_CHUNK_SIZE, configured_action_coverage=NATIVE_CHUNK_SIZE,
        request_threshold_actions=REQUEST_THRESHOLD_ACTIONS, added_delay_ms=delay,
        delay_condition="native" if delay == 0 else "plus_200ms", seed=seed,
        requested_initialization_index=0, resolved_initialization_index_or_id="PENDING_PREFLIGHT_RESOLUTION",
        initialization_index_or_id="libero_episode_index:0",
        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
        output_path=f"episodes/{run_id}.json",
    )


def stage4_manifest(provenance: Mapping[str, str]) -> list[Stage4Plan]:
    rows = [_plan(provenance, task, scene, delay, seed)
            for task in TASKS for scene in ("id", "ood")
            for delay in DELAYS_MS for seed in SEEDS]
    validate_manifest(rows)
    return rows


def validate_manifest(rows: Sequence[Stage4Plan | Mapping[str, str]]) -> None:
    def value(row, field): return getattr(row, field) if hasattr(row, field) else row[field]
    if len(rows) != 64 or len({value(r, "run_id") for r in rows}) != 64:
        raise ValueError("Stage 4 requires exactly 64 unique physical episodes")
    checks = {
        "task_key": set(TASKS), "scene": {"id", "ood"}, "added_delay_ms": set(DELAYS_MS),
        "seed": set(SEEDS), "policy_family": {POLICY_FAMILY}, "execution_method": {EXECUTION_METHOD},
        "native_chunk_size": {8}, "configured_action_coverage": {8}, "request_threshold_actions": {4},
        "requested_initialization_index": {0}, "checkpoint_id": {CHECKPOINT_ID},
        "checkpoint_revision": {CHECKPOINT_REVISION}, "openvla_oft_git_sha": {OPENVLA_OFT_COMMIT},
    }
    for field, expected in checks.items():
        numeric = bool(expected) and all(isinstance(item, int) for item in expected)
        actual = {int(value(row, field)) if numeric else value(row, field) for row in rows}
        if actual != expected: raise ValueError(f"Stage 4 {field} changed: {actual!r}")
    for row in rows:
        task = TASKS[value(row, "task_key")]
        if value(row, "scene") == "ood":
            literal = {
                "classification_id": task["classification_id"], "api_task_index": task["api_task_index"],
                "difficulty_level": task["difficulty_level"], "variant_name": task["variant_name"],
                "official_category": "Objects Layout",
            }
            for field, expected in literal.items():
                if str(value(row, field)) != str(expected): raise ValueError(f"frozen {field} changed")


def as_rows(rows: Sequence[Stage4Plan]) -> list[dict]:
    return [asdict(row) for row in rows]


def paired_interaction_values(rows: Sequence[Mapping[str, str]], task_key: str) -> list[float]:
    selected = [r for r in rows if r["task_key"] == task_key]
    values = []
    for seed in SEEDS:
        cell = {(r["scene_condition"], int(r["added_delay_ms"])): int(r["success"])
                for r in selected if int(r["seed"]) == seed}
        expected = {(s, d) for s in ("id", "ood") for d in DELAYS_MS}
        if set(cell) != expected: raise ValueError(f"incomplete paired seed cluster {task_key}/{seed}")
        values.append((cell[("ood", 200)] - cell[("ood", 0)]) - (cell[("id", 200)] - cell[("id", 0)]))
    return values
