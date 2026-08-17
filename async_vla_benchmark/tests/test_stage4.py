import pytest
from async_vla_benchmark.benchmark.stage4 import ELIGIBLE_VARIANTS, stage4_manifest


PROVENANCE={"git_sha":"a"*40,"lerobot_git_sha":"b"*40,"libero_plus_git_sha":"c"*40,
            "model_revision":"d"*40,"vlash_repository":"https://github.com/mit-han-lab/vlash",
            "vlash_revision":"e"*40,"vlash_checkpoint_id":"official-vlash-pi05-libero@"+"f"*40}


def candidate(key):
    value=ELIGIBLE_VARIANTS[key]
    result={k:str(value[k]) for k in ("task_key","perturbation_key","classification_id","api_task_index","variant_name","difficulty_level")}
    result.update({"stage3_analysis_status":"prespecified_confirmatory", "selection_frozen_before_vlash_outcomes":"True"})
    return result


def test_stage4_one_candidate_is_40_physical_episodes():
    rows=stage4_manifest([candidate("object_layout")],PROVENANCE)
    assert len(rows)==40
    assert {r.seed for r in rows}==set(range(22,27))
    assert {r.execution_method for r in rows}=={"rtc","vlash"}
    assert {r.added_delay_ms for r in rows}=={0,200}
    assert {r.configured_n_action_steps for r in rows}=={25}


def test_shared_goal_id_is_not_duplicated():
    rows=stage4_manifest([candidate("robot_initial_state"),candidate("light_conditions")],PROVENANCE)
    assert len(rows)==60  # 20 shared physical ID + 2 × 20 OOD
    assert sum(r.scene=="id" for r in rows)==20
    assert sum(r.scene=="ood" for r in rows)==40
    assert len({r.run_id for r in rows})==60


def test_different_task_ids_reach_80_maximum():
    rows=stage4_manifest([candidate("object_layout"),candidate("light_conditions")],PROVENANCE)
    assert len(rows)==80


def test_posthoc_sensor_noise_is_ineligible():
    assert "sensor_noise" not in ELIGIBLE_VARIANTS
    bad=candidate("light_conditions"); bad["perturbation_key"]="sensor_noise"
    with pytest.raises(ValueError): stage4_manifest([bad],PROVENANCE)
