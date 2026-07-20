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


def preprocess_observation(preprocessor: Any, observation: Any, task_instruction: str) -> Any:
    """Build the input batch expected by the policy preprocessor."""
    # The LeRobot preprocessor expects a dict that can be converted to an EnvTransition.
    # For LIBERO, the raw observation has pixels/robot_state and a list-style task prompt.
    batch = dict(observation)
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
    batch = preprocess_observation(preprocessor, observation, task_instruction)
    preprocessing_end_ns = time.perf_counter_ns()

    _maybe_cuda_sync()
    inference_start_ns = time.perf_counter_ns()
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
    _maybe_cuda_sync()
    inference_end_ns = time.perf_counter_ns()

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
