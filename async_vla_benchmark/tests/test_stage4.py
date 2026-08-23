import pytest

from async_vla_benchmark.benchmark.openvla_oft import resolve_unnorm_key
from async_vla_benchmark.benchmark.stage4 import (
    CHECKPOINT_ID, CHECKPOINT_REVISION, OPENVLA_OFT_COMMIT, SEEDS, TASKS,
    paired_interaction_values, stage4_manifest, validate_manifest,
)

PROVENANCE={"git_sha":"a"*40,"libero_plus_git_sha":"b"*40}


def test_stage4_exact_64_episode_matrix():
    rows=stage4_manifest(PROVENANCE)
    assert len(rows)==64 and len({r.run_id for r in rows})==64
    assert {r.task_key for r in rows}==set(TASKS)
    assert {r.scene for r in rows}=={"id","ood"}
    assert {r.added_delay_ms for r in rows}=={0,200}
    assert {r.seed for r in rows}==set(SEEDS)
    assert {r.execution_method for r in rows}=={"naive_async_openvla_oft"}
    assert {r.native_chunk_size for r in rows}=={8}
    assert {r.request_threshold_actions for r in rows}=={4}
    assert {r.checkpoint_id for r in rows}=={CHECKPOINT_ID}
    assert {r.checkpoint_revision for r in rows}=={CHECKPOINT_REVISION}
    assert {r.openvla_oft_git_sha for r in rows}=={OPENVLA_OFT_COMMIT}


def test_stage4_exact_frozen_ood_variants():
    rows=[r for r in stage4_manifest(PROVENANCE) if r.scene=="ood"]
    for task_key,expected in TASKS.items():
        selected=[r for r in rows if r.task_key==task_key]
        assert {(r.classification_id,r.api_task_index,r.difficulty_level,r.variant_name) for r in selected}=={
            (expected["classification_id"],expected["api_task_index"],expected["difficulty_level"],expected["variant_name"])
        }


def test_manifest_rejects_treatment_change():
    rows=stage4_manifest(PROVENANCE); rows[0]=rows[0].__class__(**{**rows[0].__dict__,"request_threshold_actions":5})
    with pytest.raises(ValueError): validate_manifest(rows)


def test_paired_interaction_keeps_seed_cluster_together():
    rows=[]
    for seed in SEEDS:
        values={("id",0):1,("id",200):1,("ood",0):1,("ood",200):0 if seed==38 else 1}
        for (scene,delay),success in values.items(): rows.append({"task_key":"spatial_transport","scene_condition":scene,"added_delay_ms":str(delay),"seed":str(seed),"success":str(success)})
    assert paired_interaction_values(rows,"spatial_transport")==[-1.0]+[0.0]*7


def test_suite_specific_unnorm_key_resolution():
    model=type("M",(),{"norm_stats":{"libero_spatial_no_noops":{},"libero_10":{}}})()
    assert resolve_unnorm_key(model,"libero_spatial")=="libero_spatial_no_noops"
    assert resolve_unnorm_key(model,"libero_10")=="libero_10"
    with pytest.raises(ValueError): resolve_unnorm_key(model,"libero_goal")
