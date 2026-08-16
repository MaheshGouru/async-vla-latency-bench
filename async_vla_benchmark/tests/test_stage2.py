from collections import Counter

import pytest

from async_vla_benchmark.benchmark.stage2 import (
    ADDED_DELAYS_MS, HORIZONS, SEEDS, stage2_manifest,
)
from async_vla_benchmark.benchmark.environment import initial_state_fingerprint


@pytest.fixture
def rows():
    return stage2_manifest({
        "git_sha": "a" * 40,
        "lerobot_git_sha": "b" * 40,
        "model_revision": "c" * 40,
    })


def test_stage2_frozen_matrix(rows):
    assert len(rows) == 360
    assert len({row.run_id for row in rows}) == 360
    assert {row.configured_n_action_steps for row in rows} == set(HORIZONS)
    assert {row.added_delay_ms for row in rows} == set(ADDED_DELAYS_MS)
    assert {row.seed for row in rows} == set(SEEDS)
    assert Counter(row.task_key for row in rows) == {
        "spatial_transport": 120,
        "goal_drawer": 120,
        "long_stove_moka": 120,
    }


def test_stage2_coupled_coverage_is_explicit(rows):
    assert all(row.execution_method == "rtc" and row.scene_condition == "id" for row in rows)
    assert all(row.rtc_execution_horizon == row.configured_n_action_steps for row in rows)
    assert all(row.request_threshold_actions == row.configured_n_action_steps for row in rows)
    assert all(row.analysis_status == "posthoc_sensitivity" for row in rows)
    assert all(row.initialization_index_or_id == "libero_episode_index:0" for row in rows)


def test_stage2_run_ids_encode_all_cell_dimensions(rows):
    row = rows[0]
    assert row.run_id == "stage2__spatial_transport__rtc__h10__d0__s5"


def test_reset_state_fingerprint_is_stable_and_state_sensitive():
    class Data:
        def __init__(self, values):
            self.qpos=values; self.qvel=[0.0]; self.act=[]; self.ctrl=[]
            self.mocap_pos=[]; self.mocap_quat=[]
    class Sim:
        def __init__(self, values): self.data=Data(values)
    class Env:
        def __init__(self, values): self.sim = Sim(values)
    method_a, first = initial_state_fingerprint(Env([1.0, 2.0]), {})
    method_b, second = initial_state_fingerprint(Env([1.0, 2.0]), {})
    _, changed = initial_state_fingerprint(Env([1.0, 3.0]), {})
    assert method_a == method_b == "mujoco_reset_state_v2_sha256"
    assert first == second
    assert first != changed


def test_reset_state_fingerprint_ignores_time_and_sub_tolerance_noise():
    class Data:
        qvel=[0.0]; act=[]; ctrl=[]; mocap_pos=[]; mocap_quat=[]
        def __init__(self,qpos,time): self.qpos=qpos; self.time=time
    class Sim:
        def __init__(self,qpos,time): self.data=Data(qpos,time)
    class Env:
        def __init__(self,qpos,time): self.sim=Sim(qpos,time)
    _, baseline=initial_state_fingerprint(Env([1.0],0.0),{})
    _, changed_time=initial_state_fingerprint(Env([1.0],99.0),{})
    _, tiny_noise=initial_state_fingerprint(Env([1.0+1e-14],0.0),{})
    assert baseline==changed_time==tiny_noise
