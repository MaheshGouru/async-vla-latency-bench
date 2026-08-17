from collections import Counter
import pytest
from async_vla_benchmark.benchmark.stage3b import ADDED_DELAYS_MS,HORIZONS,SEEDS,VARIANTS,stage3b_manifest

@pytest.fixture
def rows(): return stage3b_manifest({"git_sha":"a"*40,"lerobot_git_sha":"b"*40,"libero_plus_git_sha":"c"*40,"model_revision":"d"*40})

def test_frozen_new_matrix(rows):
 assert len(rows)==144 and len({r.run_id for r in rows})==144
 assert Counter(r.scene for r in rows)=={"ood":96,"id":48}
 assert {r.configured_n_action_steps for r in rows}==set(HORIZONS)=={20,25,30}
 assert {r.added_delay_ms for r in rows}==set(ADDED_DELAYS_MS)=={0,200}
 assert {r.seed for r in rows}==set(SEEDS)==set(range(14,22))

def test_control_reuse_is_physical_not_duplicated(rows):
 assert not any(r.task_key=="goal_drawer" and r.scene=="id" for r in rows)
 assert not any(r.task_key=="long_stove_moka" for r in rows)
 assert sum(r.task_key=="spatial_transport" and r.scene=="id" for r in rows)==48

def test_exact_variants(rows):
 actual={(r.task_key,r.classification_id,r.api_task_index,r.variant_name,r.difficulty_level) for r in rows if r.scene=="ood"}
 expected={(k,str(v["classification_id"]),v["api_task_index"],v["variant_name"],str(v["difficulty_level"])) for k,v in VARIANTS.items()}
 assert actual==expected

def test_six_cell_pairing_blocks(rows):
 groups={}
 for r in rows: groups.setdefault((r.task_key,r.scene,r.variant_name,r.seed),set()).add((r.configured_n_action_steps,r.added_delay_ms))
 assert len(groups)==24
 assert all(cells=={(h,d) for h in HORIZONS for d in ADDED_DELAYS_MS} for cells in groups.values())
