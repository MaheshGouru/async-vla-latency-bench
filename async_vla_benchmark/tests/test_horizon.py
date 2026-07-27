import pytest

from async_vla_benchmark.benchmark.queues import ActionQueue, QueuedAction


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
