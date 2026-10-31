from async_vla_benchmark.benchmark.environment import available_initialization_count, resolve_episode_index
from async_vla_benchmark.benchmark.stage3c import (
    AUDIT_ROWS, ENV_CONSTRUCTION_SEED, FINGERPRINT_METHOD,
    INITIALIZATION_INDICES, REPEAT_IDS, TASKS, VALIDATED_ROWS,
    assert_frozen_variants,
)
from async_vla_benchmark.scripts.validate_stage3c import validate


def frozen_rows():
    return [
        {
            "task_key": key, "suite": value["suite"],
            "base_task_id": str(value["base_task_id"]),
            "base_task_name": value["base_task_name"],
            "perturbation_key": "object_layout",
            "classification_id": str(value["classification_id"]),
            "api_task_index": str(value["api_task_index"]),
            "difficulty_level": str(value["difficulty_level"]),
            "variant_name": value["variant_name"],
        }
        for key, value in TASKS.items()
    ]


def valid_audit_rows():
    rows = []
    for task in TASKS:
        for scene in ("id", "ood"):
            for index in INITIALIZATION_INDICES:
                fingerprint = f"{task}-{scene}-{index}"
                for repeat in REPEAT_IDS:
                    rows.append({
                        "task_key": task, "scene_condition": scene,
                        "requested_initialization_index": str(index),
                        "resolved_initialization_index_or_id": str(index),
                        "available_initialization_state_count": "10",
                        "repeat_id": str(repeat),
                        "initial_state_fingerprint": fingerprint,
                        "fingerprint_schema_version": FINGERPRINT_METHOD,
                        "env_construction_seed": str(ENV_CONSTRUCTION_SEED),
                        "policy_rollout_seed": "", "policy_inference_executed": "False",
                        "action_steps_executed": "0", "variant_name_or_id": task,
                        "stage3c_spec_hash": "s", "benchmark_repo_sha": "b",
                        "libero_git_sha": "", "libero_plus_git_sha": "p",
                    })
    return rows


def test_frozen_stage3c_matrix_and_variants():
    assert AUDIT_ROWS == 144 and VALIDATED_ROWS == 48
    assert INITIALIZATION_INDICES == tuple(range(8))
    assert REPEAT_IDS == (0, 1, 2) and ENV_CONSTRUCTION_SEED == 0
    assert_frozen_variants(frozen_rows())


def test_resolved_index_walks_wrappers():
    class Inner:
        episode_index = 7
        _init_states = list(range(10))
    class Outer:
        _env = Inner()
    assert resolve_episode_index(Outer()) == 7
    assert available_initialization_count(Outer()) == 10


def test_resolved_index_detects_upstream_modulo_aliasing():
    class Env:
        episode_index = 7
        _init_states = ["only-state"]
    assert resolve_episode_index(Env()) == 0


def test_complete_deterministic_distinct_audit_passes():
    errors, certified = validate(valid_audit_rows())
    assert errors == [] and len(certified) == 48


def test_aliasing_indices_fails_closed():
    rows = valid_audit_rows()
    for row in rows:
        if row["task_key"] == "goal_drawer" and row["scene_condition"] == "id" and row["requested_initialization_index"] == "7":
            row["initial_state_fingerprint"] = "goal_drawer-id-6"
    errors, _ = validate(rows)
    assert any("8/8 distinctness failed" in error for error in errors)


def test_repeat_nondeterminism_fails_closed():
    rows = valid_audit_rows()
    rows[0]["initial_state_fingerprint"] = "different"
    errors, _ = validate(rows)
    assert any("within-index determinism failed" in error for error in errors)
