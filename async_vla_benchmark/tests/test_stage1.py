import json
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.ood_tasks import TaskVariant
from async_vla_benchmark.benchmark.stage1 import (
    read_selected_high_delay,
    stage1_plans,
)


CONFIG = Path(__file__).resolve().parents[1] / "configs" / "stage1_libero_plus.yaml"


def _fake_variants(cfg):
    assert cfg.stage1 is not None
    variants = {}
    index = 1000
    for task in cfg.stage1.tasks:
        for perturbation in cfg.stage1.perturbations:
            variants[(task.suite, perturbation.key)] = [
                TaskVariant(
                    id=index,
                    name=f"{task.task_name}_{perturbation.key}",
                    category=perturbation.category,
                    difficulty_level=cfg.stage1.difficulty_level or 1,
                )
            ]
            index += 1
    return variants


def test_stage1_plan_is_libero_plus_ood_latency_matrix():
    cfg = load_config(CONFIG)
    plans = stage1_plans(cfg, high_delay_ms=100, variants_by_suite=_fake_variants(cfg))
    assert len(plans) == 168
    assert {plan.base_task_ref for plan in plans} == {
        "libero_spatial:2",
        "libero_goal:0",
        "libero_10:2",
    }
    assert {plan.perturbation.key for plan in plans} == {
        "objects_layout",
        "camera_viewpoints",
        "robot_initial_states",
        "language_instructions",
        "light_conditions",
        "background_textures",
        "sensor_noise",
    }
    assert {plan.execution_method for plan in plans} == {"naive_async", "rtc"}
    assert {plan.latency_condition for plan in plans} == {"native", "native_plus_dstar"}
    assert {plan.added_delay_ms for plan in plans} == {0, 100}
    assert {plan.seed for plan in plans} == {0, 1}
    assert len({plan.episode_id for plan in plans}) == len(plans)


def test_stage1_reads_id_only_selected_high_delay(tmp_path):
    path = tmp_path / "selected_high_delay.json"
    path.write_text(
        json.dumps(
            {
                "high_added_delay_ms": 100,
                "selection_used_ood_results": False,
            }
        )
    )
    assert read_selected_high_delay(path) == 100
