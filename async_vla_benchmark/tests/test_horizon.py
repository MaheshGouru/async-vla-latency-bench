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
