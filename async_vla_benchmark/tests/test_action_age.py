from async_vla_benchmark.benchmark.execution import action_age_ms, action_age_steps


def test_action_age_uses_source_observation_step():
    assert [action_age_steps(step, 10) for step in (13, 14, 15)] == [3, 4, 5]
    assert action_age_ms(3, 0.1) == 300.0
