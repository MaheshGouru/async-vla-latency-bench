import pytest
import numpy as np

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

    try:
        reset_a = env_a.reset(seed=42)
        reset_b = env_b.reset(seed=42)
        # Gymnasium returns (observation, info); retain compatibility with older
        # Gym-style wrappers that returned the observation directly.
        obs_a = reset_a[0] if isinstance(reset_a, tuple) else reset_a
        obs_b = reset_b[0] if isinstance(reset_b, tuple) else reset_b

        def assert_same(left, right):
            if isinstance(left, dict):
                assert isinstance(right, dict)
                assert left.keys() == right.keys()
                for key in left:
                    assert_same(left[key], right[key])
                return
            np.testing.assert_array_equal(np.asarray(left), np.asarray(right))

        assert_same(obs_a, obs_b)
    finally:
        for env in (env_a, env_b):
            if hasattr(env, "close"):
                env.close()
