from collections import Counter
from pathlib import Path
from async_vla_benchmark.benchmark.experiment_a import (
    ANALYSIS_STATUS,BASE_TASK_NAME,DELAYS,HORIZON,SEEDS,
    experiment_a_manifest,select_variant_entries,
)

PROVENANCE={"git_sha":"a"*40,"lerobot_git_sha":"b"*40,"libero_plus_git_sha":"c"*40,"model_revision":"d"*40}


def variants():
    return [{"task_key":"long_stove_moka","suite":"libero_10","base_task_id":"2","base_task_name":BASE_TASK_NAME,"task_demand_type":"multi_stage_sequential","perturbation_key":"object_layout","official_category":"Objects Layout","mechanism_group":"trajectory_adaptation","classification_id":str(2000+i),"api_task_index":str(2100+i),"difficulty_level":"2","variant_name":f"{BASE_TASK_NAME}_add_{30+i}"} for i in range(3)]


def test_manifest_exact_matrix_and_shared_id():
    rows=experiment_a_manifest(variants(),PROVENANCE,"f"*64)
    assert len(rows)==64 and len({r["run_id"] for r in rows})==64
    assert Counter(r["scene"] for r in rows)=={"ood":48,"id":16}
    assert {int(r["seed"]) for r in rows}==set(SEEDS)
    assert {int(r["added_delay_ms"]) for r in rows}==set(DELAYS)
    assert {int(r["configured_n_action_steps"]) for r in rows}=={HORIZON}
    assert {r["analysis_status"] for r in rows}=={ANALYSIS_STATUS}
    assert len({r["variant_name"] for r in rows if r["scene"]=="id"})==1


def test_deterministic_selection_excludes_prior_and_null():
    entries=[{"id":1941,"name":BASE_TASK_NAME+"_add_25","category":"Objects Layout","difficulty_level":2},
             {"id":1999,"name":BASE_TASK_NAME+"_add_null","category":"Objects Layout","difficulty_level":None},
             {"id":12,"name":BASE_TASK_NAME+"_add_12","category":"Objects Layout","difficulty_level":3},
             {"id":11,"name":BASE_TASK_NAME+"_add_11","category":"Objects Layout","difficulty_level":2},
             {"id":10,"name":BASE_TASK_NAME+"_add_10","category":"Objects Layout","difficulty_level":2},
             {"id":9,"name":BASE_TASK_NAME+"_add_9","category":"Objects Layout","difficulty_level":1}]
    names=[e["name"] for e in entries]
    selected=select_variant_entries(entries,names)
    assert [r["classification_id"] for r in selected]==["10","11","9"]


def test_runner_has_explicit_experiment_label_and_zero_index_dispatch():
    source=(Path(__file__).parents[1]/"scripts/run_stage3.py").read_text()
    assert '"experiment_a"' in source
    assert "episode_index=0" in source
    assert 'reset_on_create=args.stage_label!="experiment_a"' in source
