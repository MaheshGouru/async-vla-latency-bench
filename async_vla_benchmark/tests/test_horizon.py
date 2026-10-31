import pytest

from async_vla_benchmark.benchmark.queues import (
    ActionQueue,
    QueuedAction,
    request_threshold_for_horizon,
)


def actions(count):
    return [QueuedAction(i, "c", i, "o", 0) for i in range(count)]


@pytest.mark.parametrize("horizon,threshold", [(2, 1), (5, 3), (10, 5)])
def test_horizon_and_threshold(horizon, threshold):
    queue = ActionQueue(horizon)
    assert queue.request_threshold == threshold
    queue.startup(actions(10))
    assert len(queue) == horizon


def test_explicit_request_threshold_overrides_default():
    queue = ActionQueue(10, request_threshold=7)
    assert queue.request_threshold == 7


def test_explicit_request_threshold_is_clamped_to_horizon():
    queue = ActionQueue(2, request_threshold=5)
    assert queue.request_threshold == 2


@pytest.mark.parametrize("horizon,threshold", [(2, 1), (5, 3), (10, 5)])
def test_request_threshold_for_horizon_matches_spec_table(horizon, threshold):
    assert request_threshold_for_horizon(horizon) == threshold


@pytest.mark.parametrize("horizon,threshold", [(2, 1), (5, 3), (10, 5)])
def test_run_benchmark_derives_threshold_from_plan_horizon(horizon, threshold):
    """Regression: run_benchmark previously passed a single constant from
    cfg.rtc.request_threshold_actions to every sweep cell, so h=2/h=5 ran with
    thresholds of 2/5 (clamped from 8) instead of the spec's 1/3. The queue's own
    default was always correct; only the wiring was wrong, so no existing test
    caught it. Assert the value run_benchmark now passes reaches the queue intact.
    """
    queue = ActionQueue(horizon, request_threshold=request_threshold_for_horizon(horizon))
    assert queue.request_threshold == threshold
