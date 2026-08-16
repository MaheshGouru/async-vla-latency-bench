import pytest

from async_vla_benchmark.benchmark.environment import (
    EnvironmentUnavailable,
    initial_state_fingerprint,
    make_libero_env,
)


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

        method_a, fingerprint_a = initial_state_fingerprint(env_a, obs_a)
        method_b, fingerprint_b = initial_state_fingerprint(env_b, obs_b)
        # GPU rasterization can differ by a handful of ±1 pixel values even
        # when the simulator state is identical. Pairing must therefore use the
        # underlying MuJoCo reset state rather than rendered-image bytes.
        assert method_a == method_b == "mujoco_sim_state_sha256"
        assert fingerprint_a == fingerprint_b
    finally:
        for env in (env_a, env_b):
            if hasattr(env, "close"):
                env.close()
