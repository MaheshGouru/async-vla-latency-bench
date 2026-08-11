from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.stage0 import (
    REFINEMENT_CELLS,
    REFINEMENT_DELAYS_MS,
    select_high_delay,
    stage0_plans,
    stage0_refinement_plans,
)


CONFIG = Path(__file__).resolve().parents[1] / "configs" / "stage0_latency_calibration.yaml"


def test_stage0_plan_is_the_frozen_96_episode_matrix():
    plans = stage0_plans(load_config(CONFIG))
    assert len(plans) == 96
    assert [plan.task_ref for plan in plans[::32]] == [
        "libero_spatial:2",
        "libero_goal:0",
        "libero_10:2",
    ]
    assert {plan.execution_method for plan in plans} == {"naive_async", "rtc"}
    assert {plan.added_delay_ms for plan in plans} == set(range(0, 701, 100))
    assert {plan.seed for plan in plans} == {0, 1}
    assert plans[0].run_id == "C001"
    assert plans[-1].run_id == "C096"
    assert len({plan.episode_id for plan in plans}) == 96


def test_stage0_primary_delay_selection_uses_smallest_eligible_delay():
    rows = []
    cells = [(f"task_{task}", method) for task in range(3) for method in ("naive_async", "rtc")]
    successes_by_delay = {0: 12, 100: 11, 200: 9, 300: 6, 400: 3, 500: 2, 600: 1, 700: 0}
    for delay, success_count in successes_by_delay.items():
        index = 0
        for task_key, method in cells:
            for seed in (0, 1):
                rows.append(
                    {
                        "task_key": task_key,
                        "execution_method": method,
                        "added_delay_ms": delay,
                        "seed": seed,
                        "success": index < success_count,
                    }
                )
                index += 1
    selected = select_high_delay(rows)
    assert selected["high_added_delay_ms"] == 200
    assert selected["selection_reason"] == "primary_rule"
    assert selected["selection_used_ood_results"] is False


def test_stage0_refinement_is_the_credit_conscious_18_episode_matrix():
    plans = stage0_refinement_plans(load_config(CONFIG))
    assert len(plans) == 18
    assert [(plan.task.task_key, plan.execution_method) for plan in plans[::6]] == list(
        REFINEMENT_CELLS
    )
    assert {plan.added_delay_ms for plan in plans} == set(REFINEMENT_DELAYS_MS)
    assert {plan.seed for plan in plans} == {0, 1}
    assert plans[0].run_id == "R001"
    assert plans[-1].run_id == "R018"
    assert all(plan.stage == "stage0_refinement_25_75" for plan in plans)
    assert len({plan.episode_id for plan in plans}) == 18


def test_refined_delay_selection_accepts_the_25ms_grid():
    rows = []
    cells = list(REFINEMENT_CELLS)
    successes_by_delay = {0: 6, 25: 5, 50: 4, 75: 3, 100: 2}
    for delay, success_count in successes_by_delay.items():
        index = 0
        for task_key, method in cells:
            for seed in (0, 1):
                rows.append(
                    {
                        "task_key": task_key,
                        "execution_method": method,
                        "added_delay_ms": delay,
                        "seed": seed,
                        "success": index < success_count,
                    }
                )
                index += 1
    selected = select_high_delay(rows, (0, 25, 50, 75, 100))
    assert selected["high_added_delay_ms"] == 50
    assert selected["selection_reason"] == "primary_rule"
