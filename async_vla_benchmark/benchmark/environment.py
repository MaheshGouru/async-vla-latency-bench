"""Lazy LIBERO environment integration and control-frequency resolution."""

from dataclasses import dataclass
from typing import Any


class EnvironmentUnavailable(RuntimeError):
    pass


def require_lerobot_libero() -> None:
    try:
        import lerobot  # noqa: F401
        import libero  # noqa: F401
    except ImportError as exc:
        raise EnvironmentUnavailable(
            "LeRobot/LIBERO is not installed. Install a pinned LeRobot checkout with "
            "the pi and libero extras in the Linux CUDA execution environment."
        ) from exc


@dataclass
class TaskInfo:
    suite: str
    task_id: int
    task_name: str
    language_instruction: str


def _find_control_freq(environment: Any) -> float | None:
    """Walk through wrappers looking for an explicit positive control frequency."""
    visited = set()
    objects = [environment]
    while objects:
        obj = objects.pop()
        obj_id = id(obj)
        if obj_id in visited:
            continue
        visited.add(obj_id)
        for attr in ("control_freq", "control_frequency"):
            value = getattr(obj, attr, None)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        unwrapped = getattr(obj, "unwrapped", None)
        if unwrapped is not None:
            objects.append(unwrapped)
        env_attr = getattr(obj, "env", None)
        if env_attr is not None:
            objects.append(env_attr)
    return None


def resolve_control_frequency_hz(environment: Any) -> float:
    """Resolve an explicitly exposed frequency; never invent a default."""
    value = _find_control_freq(environment)
    if value is not None:
        return value
    # If the underlying environment exposes no control_freq, check metadata.
    metadata = getattr(environment, "metadata", None)
    if isinstance(metadata, dict):
        for key in ("control_frequency_hz", "render_fps"):
            value = metadata.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
    raise EnvironmentUnavailable(
        "LIBERO environment did not expose a reliable control frequency; inspect the pinned "
        "environment revision and add an explicit adapter before running episodes."
    )


def make_libero_env(
    suite_name: str,
    task_id: int,
    *,
    seed: int,
    control_mode: str = "relative",
    obs_type: str = "pixels_agent_pos",
    camera_name: str = "agentview_image,robot0_eye_in_hand_image",
    observation_width: int = 224,
    observation_height: int = 224,
    init_states: bool = True,
    episode_length: int | None = None,
    num_steps_wait: int = 10,
) -> Any:
    """Build a single LIBERO environment with deterministic initial-state selection."""
    require_lerobot_libero()
    from lerobot.envs.libero import LiberoEnv, _get_suite

    suite = _get_suite(suite_name)
    env = LiberoEnv(
        task_suite=suite,
        task_id=task_id,
        task_suite_name=suite_name,
        episode_length=episode_length,
        camera_name=camera_name,
        obs_type=obs_type,
        render_mode="rgb_array",
        observation_width=observation_width,
        observation_height=observation_height,
        init_states=init_states,
        episode_index=0,
        n_envs=1,
        num_steps_wait=num_steps_wait,
        control_mode=control_mode,
    )
    env.reset(seed=seed)
    return env


def make_libero_plus_env(
    suite_name: str,
    task_id: int,
    *,
    seed: int,
    control_mode: str = "relative",
    obs_type: str = "pixels_agent_pos",
    camera_name: str = "agentview_image,robot0_eye_in_hand_image",
    observation_width: int = 224,
    observation_height: int = 224,
    init_states: bool = True,
    episode_length: int | None = None,
    num_steps_wait: int = 10,
) -> Any:
    """Build a single LIBERO-plus environment (OOD perturbation variant).

    Identical to `make_libero_env` except it passes `is_libero_plus=True` to
    LeRobot's `LiberoEnv`, which switches its init-state file resolution to
    LIBERO-plus's naming/layout. This requires the LIBERO-plus fork to be the
    installed `libero` package (see Dockerfile.modal.libero_plus) rather than
    the vanilla `hf-libero` package that `make_libero_env` runs against; the
    two cannot be installed side by side.

    `suite_name`/`task_id` still index into whatever `benchmark.get_benchmark_dict()`
    returns for the installed package, so `task_id` selects a specific LIBERO-plus
    task/perturbation variant, not a base LIBERO task uniformly across categories.
    Use `benchmark.ood_tasks` to resolve which `task_id` corresponds to which
    perturbation category/difficulty for a given suite.
    """
    require_lerobot_libero()
    from lerobot.envs.libero import LiberoEnv, _get_suite

    suite = _get_suite(suite_name)
    env = LiberoEnv(
        task_suite=suite,
        task_id=task_id,
        task_suite_name=suite_name,
        episode_length=episode_length,
        camera_name=camera_name,
        obs_type=obs_type,
        render_mode="rgb_array",
        observation_width=observation_width,
        observation_height=observation_height,
        init_states=init_states,
        episode_index=0,
        n_envs=1,
        num_steps_wait=num_steps_wait,
        control_mode=control_mode,
        is_libero_plus=True,
    )
    env.reset(seed=seed)
    return env


def get_task_info(env: Any, suite_name: str, task_id: int) -> TaskInfo:
    """Extract the task name and language instruction from the environment."""
    task_name = getattr(env, "task", "")
    instruction = getattr(env, "task_description", "")
    if not task_name or not instruction:
        task = getattr(env, "_task", None)
        if task is not None:
            task_name = getattr(task, "name", task_name)
            instruction = getattr(task, "language", instruction)
    return TaskInfo(
        suite=suite_name,
        task_id=task_id,
        task_name=task_name or f"{suite_name}_{task_id}",
        language_instruction=instruction or "",
    )


def get_max_episode_steps(env: Any) -> int:
    """Return the environment's maximum episode length or a safe fallback."""
    value = getattr(env, "_max_episode_steps", None)
    if isinstance(value, int) and value > 0:
        return value
    return 520
