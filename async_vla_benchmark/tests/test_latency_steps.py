from async_vla_benchmark.benchmark.latency import latency_to_delay_steps


def test_latency_deadlines_at_100_ms_control_period():
    expected = {0: 0, 1: 1, 100: 1, 101: 2, 300: 3, 700: 7}
    for latency_ms, steps in expected.items():
        assert latency_to_delay_steps(latency_ms, 0.1) == steps
