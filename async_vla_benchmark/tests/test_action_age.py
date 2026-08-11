from types import SimpleNamespace

from async_vla_benchmark.benchmark.execution import EpisodeRunner, action_age_ms, action_age_steps
from async_vla_benchmark.benchmark.latency import LatencyProfile


def test_action_age_uses_source_observation_step():
    assert [action_age_steps(step, 10) for step in (13, 14, 15)] == [3, 4, 5]
    assert action_age_ms(3, 0.1) == 300.0


def test_hold_actions_do_not_bias_episode_action_age_to_zero():
    runner = EpisodeRunner.__new__(EpisodeRunner)
    runner.summary_metadata = {}
    runner.episode_id = "episode"
    runner.strategy = "naive_async"
    runner.latency_profile = LatencyProfile("native", True, 0)
    runner.fixed_horizon = 10
    runner.max_steps = 10
    runner.control_frequency_hz = 20.0
    runner.control_period_seconds = 0.05
    runner._wall_clock_runtime_seconds = 1.0
    runner._total_model_inference_ms = 10.0
    runner.use_rtc = False
    runner.queue = SimpleNamespace(discarded_old_actions=0)
    runner.requests = [
        {"measured_request_latency_ms": 100.0, "delay_steps": 2, "latency_profile": "native"}
    ]
    runner.actions = [
        {
            "action_age_ms": None,
            "queue_depth_before": 0,
            "is_queue_underrun": True,
            "is_hold_action": True,
            "action_vector": [0.0] * 7,
        },
        {
            "action_age_ms": 400.0,
            "queue_depth_before": 2,
            "is_queue_underrun": False,
            "is_hold_action": False,
            "action_vector": [0.1] * 7,
        },
        {
            "action_age_ms": 600.0,
            "queue_depth_before": 1,
            "is_queue_underrun": False,
            "is_hold_action": False,
            "action_vector": [0.2] * 7,
        },
    ]
    summary = runner._summarize(False, 3)
    assert summary["mean_action_age_ms"] == 500.0
    assert summary["p50_action_age_ms"] == 500.0
