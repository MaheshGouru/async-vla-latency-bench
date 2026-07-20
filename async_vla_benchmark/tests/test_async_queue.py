import pytest

from async_vla_benchmark.benchmark.queues import ActionQueue, QueuedAction


def chunk(chunk_id, count=10):
    return [QueuedAction(i, chunk_id, i, "obs", 0) for i in range(count)]


def test_old_actions_continue_then_remainder_is_replaced():
    queue = ActionQueue(10)
    queue.startup(chunk("old"))
    for _ in range(5):
        assert queue.pop().chunk_id == "old"
    assert queue.should_request()
    queue.begin_request("r1")
    assert queue.pop().chunk_id == "old"
    with pytest.raises(RuntimeError):
        queue.begin_request("r2")
    queue.replace("r1", chunk("new"))
    assert queue.discarded_old_actions == 4
    assert queue.pop().chunk_id == "new"


def test_empty_queue_signals_underrun_to_caller():
    queue = ActionQueue(2)
    queue.startup(chunk("old", 2))
    queue.pop()
    queue.pop()
    assert queue.pop() is None
