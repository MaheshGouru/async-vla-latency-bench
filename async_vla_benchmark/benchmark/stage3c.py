"""Frozen Stage 3C reset-only initialization audit."""
from __future__ import annotations

TASKS = {
    "spatial_transport": {
        "suite": "libero_spatial", "base_task_id": 2,
        "base_task_name": "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate",
        "classification_id": 1773, "api_task_index": 1772, "difficulty_level": 3,
        "variant_name": "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15",
    },
    "goal_drawer": {
        "suite": "libero_goal", "base_task_id": 0,
        "base_task_name": "open_the_middle_drawer_of_the_cabinet",
        "classification_id": 1891, "api_task_index": 1890, "difficulty_level": 2,
        "variant_name": "open_the_middle_drawer_of_the_cabinet_add_13",
    },
    "long_stove_moka": {
        "suite": "libero_10", "base_task_id": 2,
        "base_task_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",
        "classification_id": 1941, "api_task_index": 1940, "difficulty_level": 2,
        "variant_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25",
    },
}
INITIALIZATION_INDICES = tuple(range(8))
REPEAT_IDS = tuple(range(3))
ENV_CONSTRUCTION_SEED = 0
FINGERPRINT_METHOD = "mujoco_reset_state_v2_sha256"
FINGERPRINT_SCHEMA = (
    "qpos,qvel,act,ctrl,mocap_pos,mocap_quat; float64 little-endian; "
    "round=1e-12; excludes sim time"
)
AUDIT_ROWS = len(TASKS) * 2 * len(INITIALIZATION_INDICES) * len(REPEAT_IDS)
VALIDATED_ROWS = len(TASKS) * 2 * len(INITIALIZATION_INDICES)


def expected_variant_rows():
    return {
        (
            key, value["suite"], str(value["base_task_id"]), value["base_task_name"],
            str(value["classification_id"]), str(value["api_task_index"]),
            str(value["difficulty_level"]), value["variant_name"],
        )
        for key, value in TASKS.items()
    }


def assert_frozen_variants(rows) -> None:
    actual = {
        (
            row["task_key"], row["suite"], row["base_task_id"], row["base_task_name"],
            row["classification_id"], row["api_task_index"], row["difficulty_level"],
            row["variant_name"],
        )
        for row in rows if row.get("task_key") in TASKS and row.get("perturbation_key") == "object_layout"
    }
    if actual != expected_variant_rows():
        raise ValueError("Stage 1 frozen object-layout identities do not exactly match Stage 3C")
