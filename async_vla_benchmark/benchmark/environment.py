"""Lazy LIBERO environment integration and control-frequency resolution."""

import hashlib
from dataclasses import dataclass
from typing import Any


class EnvironmentUnavailable(RuntimeError):
    pass


def seed_environment_rng(seed: int) -> None:
    """Seed process-global RNGs consumed by LIBERO/robosuite reset logic."""
    import random
    import numpy as np

    random.seed(seed)
    np.random.seed(seed)


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


def initial_state_fingerprint(environment: Any, observation: Any) -> tuple[str, str]:
    """Return a stable fingerprint of the MuJoCo reset state.

    The wrapper stack differs across LeRobot/LIBERO releases, so walk common
    wrapper links and prefer the simulator's complete flattened state. A
    policy-observation hash is a fail-closed fallback when the pinned wrapper
    exposes no simulator object. The method is returned with the digest so a
    manifest never silently mixes the two representations.
    """
    import numpy as np

    visited: set[int] = set()
    pending = [environment]
    while pending:
        obj = pending.pop()
        if obj is None or id(obj) in visited:
            continue
        visited.add(id(obj))
        sim = getattr(obj, "sim", None)
        if sim is not None:
            try:
                # Versioned, named, scientifically relevant reset state. Exclude
                # sim time and Python/object serialization. Canonical rounding at
                # 1e-12 suppresses insignificant platform noise while remaining
                # far below any meaningful LIBERO initialization displacement.
                data = sim.data
                components = ("qpos", "qvel", "act", "ctrl", "mocap_pos", "mocap_quat")
                digest = hashlib.sha256(b"mujoco_reset_state_v2\0round_decimals=12\0")
                found = 0
                for name in components:
                    value = getattr(data, name, None)
                    if value is None:
                        continue
                    values = np.asarray(value, dtype=np.float64)
                    canonical = np.ascontiguousarray(np.round(values, decimals=12))
                    canonical[canonical == 0] = 0.0  # normalize negative zero
                    digest.update(name.encode() + b"\0")
                    digest.update(str(canonical.shape).encode() + b"\0")
                    digest.update(canonical.astype("<f8", copy=False).tobytes(order="C"))
                    found += 1
                if found < 2:
                    raise RuntimeError("MuJoCo simulator exposed insufficient named reset state")
                return "mujoco_reset_state_v2_sha256", digest.hexdigest()
            except Exception:
                pass
        for attr in ("env", "_env", "unwrapped"):
            child = getattr(obj, attr, None)
            if child is not None and child is not obj:
                pending.append(child)

    digest = hashlib.sha256()

    def update(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                update(value[key], f"{path}/{key}")
            return
        try:
            array = np.asarray(value)
        except Exception:
            return
        if array.dtype.kind not in "biufc":
            return
        canonical = np.ascontiguousarray(array)
        if canonical.dtype.kind in "fc":
            canonical = np.ascontiguousarray(np.round(canonical.astype(np.float64), decimals=12))
            canonical[canonical == 0] = 0.0
        digest.update(path.encode())
        digest.update(str(canonical.shape).encode())
        digest.update(str(canonical.dtype).encode())
        digest.update(canonical.tobytes(order="C"))

    update(observation, "observation")
    return "reset_observation_sha256", digest.hexdigest()


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
    episode_index: int = 0,
    reset_on_create: bool = True,
) -> Any:
    """Build a single LIBERO environment with deterministic initial-state selection."""
    seed_environment_rng(seed)
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
        episode_index=episode_index,
        n_envs=1,
        num_steps_wait=num_steps_wait,
        control_mode=control_mode,
    )
    if reset_on_create:
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
    episode_index: int = 0,
    reset_on_create: bool = True,
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
    seed_environment_rng(seed)
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
        episode_index=episode_index,
        n_envs=1,
        num_steps_wait=num_steps_wait,
        control_mode=control_mode,
        is_libero_plus=True,
    )
    if reset_on_create:
        env.reset(seed=seed)
    return env


def available_initialization_count(environment: Any) -> int:
    """Return the number of init states exposed by the pinned LIBERO wrapper."""
    visited: set[int] = set()
    pending = [environment]
    while pending:
        obj = pending.pop()
        if obj is None or id(obj) in visited:
            continue
        visited.add(id(obj))
        init_states = getattr(obj, "_init_states", None)
        if init_states is not None:
            try:
                count = len(init_states)
            except TypeError:
                count = 0
            if count <= 0:
                raise EnvironmentUnavailable("LIBERO exposed an empty initialization array")
            return count
        for name in ("env", "_env", "unwrapped"):
            child = getattr(obj, name, None)
            if child is not None and child is not obj:
                pending.append(child)
    raise EnvironmentUnavailable("LIBERO did not expose its initialization array")


def resolve_episode_index(environment: Any) -> int:
    """Read the init-state array index actually selected by LIBERO.

    Stage 3C must verify resolution rather than assume that passing an index to
    a constructor prevents clamping, wrapping, or fallback. The pinned wrapper
    selects ``_init_states[episode_index % len(_init_states)]``; reproduce that
    resolution explicitly so an out-of-range request cannot masquerade as the
    requested state merely because ``episode_index`` retains its input value.
    """
    from numbers import Integral

    visited: set[int] = set()
    pending = [environment]
    while pending:
        obj = pending.pop()
        if obj is None or id(obj) in visited:
            continue
        visited.add(id(obj))
        for name in ("episode_index", "_episode_index"):
            value = getattr(obj, name, None)
            if isinstance(value, Integral) and not isinstance(value, bool):
                requested = int(value)
                return requested % available_initialization_count(environment)
        for name in ("env", "_env", "unwrapped"):
            child = getattr(obj, name, None)
            if child is not None and child is not obj:
                pending.append(child)
    raise EnvironmentUnavailable(
        "LIBERO did not expose the resolved episode_index; Stage 3C cannot "
        "verify requested-index dispatch and therefore fails closed."
    )


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
