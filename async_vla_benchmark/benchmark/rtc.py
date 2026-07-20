"""Thin RTC adapter for the installed LeRobot policy API."""

import inspect
from typing import Any


def configure_rtc(policy: Any, rtc_config: Any) -> None:
    policy.config.rtc_config = rtc_config
    if not hasattr(policy, "init_rtc_processor"):
        raise RuntimeError("installed policy has no init_rtc_processor RTC API")
    policy.init_rtc_processor()


def predict_rtc_chunk(
    policy: Any,
    observation: Any,
    *,
    delay_steps: int,
    previous_chunk_remainder: Any,
    execution_horizon: int,
) -> Any:
    method = getattr(policy, "predict_action_chunk", None)
    if method is None:
        raise RuntimeError("installed policy has no predict_action_chunk method")
    signature = inspect.signature(method)
    accepts_kwargs = any(p.kind == p.VAR_KEYWORD for p in signature.parameters.values())
    required = {"inference_delay", "prev_chunk_left_over", "execution_horizon"}
    if not accepts_kwargs and not required.issubset(signature.parameters):
        raise RuntimeError(
            "installed RTC API cannot accept request-specific delay, previous remainder, "
            "and execution horizon"
        )
    return method(
        observation,
        inference_delay=delay_steps,
        prev_chunk_left_over=previous_chunk_remainder,
        execution_horizon=execution_horizon,
    )
