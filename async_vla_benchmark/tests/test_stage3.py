from collections import Counter
import inspect
import pytest
from async_vla_benchmark.benchmark.stage3 import ADDED_DELAYS_MS,HORIZONS,OOD_VARIANTS,SEEDS,stage3_manifest
from async_vla_benchmark.scripts.analyze_stage3 import paired_interaction_values
from async_vla_benchmark.scripts.run_stage3 import _artifact_state, _select
from async_vla_benchmark.benchmark.execution import ExecutionEngine

@pytest.fixture
def rows(): return stage3_manifest({"git_sha":"a"*40,"lerobot_git_sha":"b"*40,"libero_plus_git_sha":"c"*40,"model_revision":"d"*40})

def test_frozen_matrix(rows):
    assert len(rows)==288 and len({r.run_id for r in rows})==288
    assert {r.configured_n_action_steps for r in rows}==set(HORIZONS)=={20,25,30}
    assert {r.added_delay_ms for r in rows}==set(ADDED_DELAYS_MS)=={0,200}
    assert {r.seed for r in rows}==set(SEEDS)==set(range(14,22))
    assert Counter(r.scene for r in rows)=={"ood":192,"id":96}

def test_exact_variants_and_status(rows):
    expected={(str(v["classification_id"]),v["api_task_index"],v["variant_name"],v["analysis_status"]) for v in OOD_VARIANTS}
    actual={(r.classification_id,r.api_task_index,r.variant_name,r.analysis_status) for r in rows if r.scene=="ood"}
    assert actual==expected
    assert sum(r.analysis_status=="posthoc_replication" for r in rows)==48
    assert sum(r.analysis_status=="prespecified_confirmatory" for r in rows)==240
    keys={(r.scene,r.task_key,r.variant_name,r.configured_n_action_steps,r.added_delay_ms,r.seed) for r in rows}
    assert len(keys)==288

def test_shared_id_and_coupled_rtc(rows):
    assert sum(r.scene=="id" for r in rows)==96
    assert all(r.execution_method=="rtc" for r in rows)
    assert all(r.rtc_execution_horizon==r.configured_n_action_steps for r in rows)
    assert all(r.request_threshold_actions==r.configured_n_action_steps for r in rows)


def test_rtc_delay_estimate_is_request_specific_and_causal():
    source=inspect.getsource(ExecutionEngine._estimate_inference_delay_steps)
    assert 'self.requests' in source
    assert 'measured_request_latency_ms' in source
    assert 'estimate_inference_delay_steps' in source


def test_interaction_uses_correct_horizon_seed_and_shared_id():
    rows=[]
    # Seed 1: OOD loses under delay, ID unchanged => -1. Seed 2: ID gains,
    # OOD unchanged => -1. Distractor horizon and task rows must be ignored.
    values={(1,"id",0):0,(1,"id",200):0,(1,"ood",0):1,(1,"ood",200):0,
            (2,"id",0):0,(2,"id",200):1,(2,"ood",0):1,(2,"ood",200):1}
    for (seed,scene,delay),success in values.items():
        rows.append({"task_key":"goal_drawer","perturbation_key":"id" if scene=="id" else "light_conditions",
            "scene_condition":scene,"configured_n_action_steps":"25","added_delay_ms":str(delay),"seed":str(seed),"success":str(success)})
    rows += [{**rows[0],"configured_n_action_steps":"20","success":"1"},
             {**rows[0],"task_key":"long_stove_moka","success":"1"}]
    assert paired_interaction_values(rows,"goal_drawer","light_conditions",25,seeds=(1,2))==[-1,-1]


def test_resume_rejects_partial_or_corrupt_artifacts(tmp_path):
    assert _artifact_state(tmp_path,"episode") == "missing"
    for folder in ("episodes","requests","actions"): (tmp_path/folder).mkdir()
    (tmp_path/"episodes/episode.json").write_text("not json")
    (tmp_path/"requests/episode.parquet").write_bytes(b"bad")
    (tmp_path/"actions/episode.parquet").write_bytes(b"bad")
    assert _artifact_state(tmp_path,"episode") == "invalid"


def test_resume_accepts_complete_triplet_then_detects_corruption(tmp_path):
    pd=pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    for folder in ("episodes","requests","actions"): (tmp_path/folder).mkdir()
    (tmp_path/"episodes/episode.json").write_text('{"episode_id":"episode"}')
    pd.DataFrame({"request_id":["r0"]}).to_parquet(tmp_path/"requests/episode.parquet")
    pd.DataFrame({"action_id":["a0"]}).to_parquet(tmp_path/"actions/episode.parquet")
    assert _artifact_state(tmp_path,"episode") == "valid"
    (tmp_path/"requests/episode.parquet").write_bytes(b"interrupted write")
    assert _artifact_state(tmp_path,"episode") == "invalid"


def test_manifest_is_independent_of_stage2_files(rows,tmp_path):
    (tmp_path/"stage2_results.csv").write_text("would,not,be,read\n")
    again=stage3_manifest({"git_sha":"a"*40,"lerobot_git_sha":"b"*40,"libero_plus_git_sha":"c"*40,"model_revision":"d"*40})
    assert [r.run_id for r in again]==[r.run_id for r in rows]


def test_scene_shards_are_order_independent(rows):
    dictionaries=[r.__dict__ for r in rows]
    id_ids={r["run_id"] for r in _select(dictionaries,"scene",["id"])}
    ood_ids={r["run_id"] for r in _select(dictionaries,"scene",["ood"])}
    assert not id_ids & ood_ids
    assert id_ids | ood_ids == {r.run_id for r in rows}
    assert len(id_ids)==96 and len(ood_ids)==192
