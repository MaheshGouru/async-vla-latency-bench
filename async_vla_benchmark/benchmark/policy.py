"""Lazy π0.5 loading with mandatory checkpoint revision and CUDA checks."""

import time
from typing import Any


def _maybe_cuda_sync():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except ImportError:
        pass
    return None


def _cuda_available() -> bool:
    try:
        import torch
    except ImportError:
        return False
    return torch.cuda.is_available()


def _new_cuda_events():
    """Create a (start, end) CUDA event pair for GPU-side inference timing.

    Spec §7 requires both a GPU event time and the complete wall-clock request
    time to be recorded; wall-clock alone cannot show whether the measurement
    was actually synchronized. Returns (None, None) off CUDA.
    """
    if not _cuda_available():
        return None, None
    import torch

    return torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)


def _cuda_event_elapsed_ms(start_event, end_event):
    """Elapsed GPU time between two recorded events, in ms.

    Must be called only after a synchronize(), which is what makes the value
    meaningful -- an unsynchronized read would race the still-running kernels.
    """
    if start_event is None or end_event is None:
        return None
    return float(start_event.elapsed_time(end_event))


def load_pi05_policy(checkpoint: str, revision: str, n_action_steps: int = 10, device: str = "cuda") -> Any:
    if not revision:
        raise ValueError("checkpoint_revision must be pinned before loading the policy")
    try:
        import torch
        from lerobot.policies.pi05.configuration_pi05 import PI05Config
        from lerobot.policies.pi05.modeling_pi05 import PI05Policy
    except ImportError as exc:
        raise RuntimeError("LeRobot π0.5 dependencies are not installed") from exc
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("the Days 1–3 benchmark requires a CUDA device")

    config = PI05Config.from_pretrained(checkpoint, revision=revision)
    config.device = device
    config.n_action_steps = n_action_steps
    # The checkpoint's own config.json bakes in compile_model=True, compile_mode="max-autotune",
    # which re-runs torch.compile's full Inductor autotune search from scratch on every process
    # start (Modal containers are ephemeral, so the Inductor cache never persists). That autotune
    # search stalled every prior run for 20+ minutes before reaching a single LIBERO episode.
    # Eval/inference doesn't need compiled sample_actions/forward, so disable it.
    config.compile_model = False
    policy = PI05Policy.from_pretrained(checkpoint, revision=revision, config=config)
    policy.to(device)
    policy.eval()
    return policy


def load_pre_post_processors(policy: Any, checkpoint: str, revision: str | None = None):
    try:
        from lerobot.policies.factory import make_pre_post_processors
    except ImportError as exc:
        raise RuntimeError("LeRobot processor factory is not available") from exc
    return make_pre_post_processors(policy.config, pretrained_path=checkpoint, pretrained_revision=revision)


def _quat_to_axisangle(quat: Any) -> Any:
    """Convert a robosuite-style (x, y, z, w) quaternion to a 3D axis-angle vector.

    Matches robosuite.utils.transform_utils.quat2axisangle, which is the convention
    the `lerobot/pi05_libero_finetuned` training data (via OpenPI's LIBERO state
    definition) was built on.
    """
    import math
    import numpy as np

    quat = np.array(quat, dtype=np.float64, copy=True)
    quat[3] = min(1.0, max(-1.0, quat[3]))
    den = math.sqrt(1.0 - quat[3] * quat[3])
    if math.isclose(den, 0.0):
        return np.zeros(3, dtype=np.float32)
    return ((quat[:3] * 2.0 * math.acos(quat[3])) / den).astype(np.float32)


def _libero_state_vector(observation: Any) -> Any:
    """Build the 8-dim [eef_pos(3), eef_axisangle(3), gripper_qpos(2)] state vector
    that `lerobot/pi05_libero_finetuned` expects as `observation.state`."""
    import numpy as np

    robot_state = observation["robot_state"]
    eef = robot_state["eef"]
    gripper = robot_state["gripper"]
    return np.concatenate(
        [
            np.asarray(eef["pos"], dtype=np.float32),
            _quat_to_axisangle(eef["quat"]),
            np.asarray(gripper["qpos"], dtype=np.float32),
        ]
    )


def _correct_libero_image_orientation(pixels: Any) -> Any:
    """Flip each camera image on both axes to match the orientation the checkpoint
    was trained on.

    LeRobot's `LiberoEnv._format_raw_obs` (the path that builds policy observations)
    hands out the raw MuJoCo/EGL camera buffer unmodified, which comes out rotated
    180 degrees. `LiberoEnv.render()` corrects for this with `image[::-1, ::-1]`
    ("flip both H and W for visualization") but that correction is never applied to
    the observation the policy actually sees. Verified by comparing a captured
    `agentview`/wrist frame against the matching episode in the checkpoint's own
    training data (`HuggingFaceVLA/libero`): both cameras were flipped on both axes
    relative to training, which explains confident-but-wrong actions (near-zero
    LIBERO success despite well-formed, non-degenerate action chunks).
    """
    import numpy as np

    # `[::-1, ::-1]` alone produces a negative-stride view, which torch.from_numpy
    # (used downstream in LeRobot's batch conversion) can't wrap directly.
    return {name: np.ascontiguousarray(image[::-1, ::-1]) for name, image in pixels.items()}


def preprocess_observation(preprocessor: Any, observation: Any, task_instruction: str) -> Any:
    """Build the input batch expected by the policy preprocessor."""
    # LiberoEnv observations use raw gym-style keys ("pixels", "robot_state"). The
    # LeRobot processor pipeline's batch_to_transition only recognizes keys prefixed
    # with "observation.", so route through LeRobot's own env-observation converter
    # before handing the batch to the preprocessor. "agent_pos" is the key that
    # converter maps to the canonical `observation.state`; the checkpoint's own
    # `observation.robot_state` is not one of its trained-on features, so drop it
    # rather than pass through an unrecognized key.
    from lerobot.envs.utils import preprocess_observation as to_lerobot_batch

    raw = dict(observation)
    raw["pixels"] = _correct_libero_image_orientation(observation["pixels"])
    raw["agent_pos"] = _libero_state_vector(observation)
    raw.pop("robot_state", None)
    batch = to_lerobot_batch(raw)
    if "task" not in batch:
        batch["task"] = [task_instruction]
    return preprocessor(batch)


def timed_request(
    policy: Any,
    preprocessor: Any,
    postprocessor: Any,
    observation: Any,
    task_instruction: str,
    *,
    delay_steps: int = 0,
    previous_chunk_remainder: Any = None,
    execution_horizon: int | None = None,
    use_rtc: bool = False,
) -> tuple[Any, Any, dict[str, float]]:
    """Run one policy request and return raw chunk, postprocessed chunk, and timing."""
    import numpy as np
    import torch

    observation_capture_ns = time.perf_counter_ns()
    preprocessing_start_ns = time.perf_counter_ns()
    if hasattr(policy, "prepare_observation"):
        batch = policy.prepare_observation(observation, task_instruction)
    else:
        batch = preprocess_observation(preprocessor, observation, task_instruction)
    preprocessing_end_ns = time.perf_counter_ns()

    # Spec §7: synchronize before the measured inference, time it with CUDA
    # events as well as the wall clock, then synchronize after.
    _maybe_cuda_sync()
    cuda_start_event, cuda_end_event = _new_cuda_events()
    inference_start_ns = time.perf_counter_ns()
    if cuda_start_event is not None:
        cuda_start_event.record()
    with torch.no_grad():
        if use_rtc:
            raw_chunk = predict_rtc_chunk(
                policy,
                batch,
                delay_steps=delay_steps,
                previous_chunk_remainder=previous_chunk_remainder,
                execution_horizon=execution_horizon,
            )
        else:
            raw_chunk = policy.predict_action_chunk(batch)
    if cuda_end_event is not None:
        cuda_end_event.record()
    _maybe_cuda_sync()
    inference_end_ns = time.perf_counter_ns()
    # Read the events only after the synchronize above; that ordering is what
    # the validator's CUDA-synchronization check asserts.
    gpu_event_ms = _cuda_event_elapsed_ms(cuda_start_event, cuda_end_event)

    postprocessing_start_ns = time.perf_counter_ns()
    processed = postprocessor(raw_chunk)
    # Convert the postprocessor output to a NumPy array if needed.
    if hasattr(processed, "action"):
        processed = processed.action
    if hasattr(processed, "numpy"):
        processed = processed.numpy(force=True)
    if processed.ndim == 3 and processed.shape[0] == 1:
        processed = processed[0]
    if not isinstance(raw_chunk, np.ndarray):
        raw_chunk = raw_chunk.detach().cpu().numpy()
    if raw_chunk.ndim == 3 and raw_chunk.shape[0] == 1:
        raw_chunk = raw_chunk[0]
    postprocessing_end_ns = time.perf_counter_ns()
    request_complete_ns = time.perf_counter_ns()

    timing = {
        "observation_capture_time": observation_capture_ns,
        "preprocessing_start_time": preprocessing_start_ns,
        "preprocessing_end_time": preprocessing_end_ns,
        "inference_start_time": inference_start_ns,
        "inference_end_time": inference_end_ns,
        "postprocessing_end_time": postprocessing_end_ns,
        "request_complete_time": request_complete_ns,
        "preprocessing_latency_ms": (preprocessing_end_ns - preprocessing_start_ns) / 1e6,
        "model_latency_ms": (inference_end_ns - inference_start_ns) / 1e6,
        "postprocessing_latency_ms": (postprocessing_end_ns - inference_end_ns) / 1e6,
        "request_latency_ms": (request_complete_ns - observation_capture_ns) / 1e6,
        # Spec §7: GPU event time alongside the wall-clock request time.
        # None off CUDA; cuda_synchronized records that the surrounding
        # synchronize() calls ran, which is what makes the event time valid.
        "gpu_event_ms": gpu_event_ms,
        "cuda_synchronized": gpu_event_ms is not None,
    }
    return raw_chunk, processed, timing


def predict_rtc_chunk(
    policy: Any,
    observation: Any,
    *,
    delay_steps: int,
    previous_chunk_remainder: Any,
    execution_horizon: int,
) -> Any:
    """Thin RTC adapter for the installed LeRobot policy API."""
    from .rtc import predict_rtc_chunk as _rtc_predict

    return _rtc_predict(
        policy,
        observation,
        delay_steps=delay_steps,
        previous_chunk_remainder=previous_chunk_remainder,
        execution_horizon=execution_horizon,
    )
