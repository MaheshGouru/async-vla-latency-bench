import pytest

from async_vla_benchmark.benchmark.environment import EnvironmentUnavailable, make_libero_env


def test_same_seed_yields_same_initial_state():
    """Verify that the same task, task_id, and seed produce the same initial simulator state.

    This test is skipped if LeRobot/LIBERO is not installed.
    """
    try:
        env_a = make_libero_env(
            "libero_spatial",
            0,
            seed=42,
            control_mode="relative",
            obs_type="pixels_agent_pos",
        )
        env_b = make_libero_env(
            "libero_spatial",
            0,
            seed=42,
            control_mode="relative",
            obs_type="pixels_agent_pos",
        )
    except EnvironmentUnavailable:
        pytest.skip("LeRobot/LIBERO not installed")

    obs_a = env_a.reset(seed=42)
    obs_b = env_b.reset(seed=42)
    assert obs_a.keys() == obs_b.keys()
    for key in obs_a:
        if isinstance(obs_a[key], dict):
            for sub in obs_a[key]:
                assert (obs_a[key][sub] == obs_b[key][sub]).all()
        else:
            assert (obs_a[key] == obs_b[key]).all()
