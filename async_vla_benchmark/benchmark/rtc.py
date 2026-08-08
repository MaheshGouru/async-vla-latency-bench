"""Thin RTC adapter for the installed LeRobot policy API."""

import inspect
from typing import Any


def build_rtc_config(
    *,
    execution_horizon: int,
    max_guidance_weight: float,
    prefix_attention_schedule: str,
) -> Any:
    """Build LeRobot's `RTCConfig` from the spec §15 settings.

    `prefix_attention_schedule` is resolved by name against LeRobot's
    `RTCAttentionSchedule` enum; note LeRobot's own default is LINEAR, while
    spec §15 requires EXP, so this must be set explicitly rather than left to
    the library default.
    """
    from lerobot.configs import RTCAttentionSchedule
    from lerobot.policies.rtc.configuration_rtc import RTCConfig

    try:
        schedule = RTCAttentionSchedule[prefix_attention_schedule.upper()]
    except KeyError as exc:
        valid = ", ".join(sorted(s.name for s in RTCAttentionSchedule))
        raise ValueError(
            f"unknown prefix_attention_schedule {prefix_attention_schedule!r}; expected one of {valid}"
        ) from exc

    return RTCConfig(
        enabled=True,
        prefix_attention_schedule=schedule,
        max_guidance_weight=max_guidance_weight,
        execution_horizon=execution_horizon,
    )


def configure_rtc(policy: Any, rtc_config: Any) -> None:
    """Attach an RTCConfig to the policy and build its RTC processor.

    Without this, `PI05Config.rtc_config` stays None (its default, and what the
    pi05_libero_finetuned checkpoint ships), `_rtc_enabled()` returns False, and
    `euler_integrate` receives `rtc_enabled=False` -- so the inference_delay,
    prev_chunk_left_over, and execution_horizon arguments are forwarded but
    never used, and no RTC guidance is applied.
    """
    policy.config.rtc_config = rtc_config
    if not hasattr(policy, "init_rtc_processor"):
        raise RuntimeError("installed policy has no init_rtc_processor RTC API")
    policy.init_rtc_processor()
    if not policy.config.rtc_config.enabled or getattr(policy, "rtc_processor", None) is None:
        raise RuntimeError("RTC configuration did not produce an active RTC processor")


def rtc_action_counts(
    *,
    inference_delay_steps: int,
    overlap_actions: int,
    execution_horizon: int,
) -> dict[str, int]:
    """Spec section 15.7: the overlapping and guided action counts for one request.

    `overlap_actions` is the length of `prev_chunk_left_over` -- the unexecuted
    remainder of the previous chunk, which is the prefix RTC is asked to stay
    consistent with. Guidance can only cover that remainder, and LeRobot clamps
    `execution_horizon` down to its length, so the horizon actually in force is
    `min(execution_horizon, overlap_actions)` rather than the configured value.
    Recording it per request turns `days1_3_audit.md`'s open risk (the effective
    horizon being silently smaller than configured) into a measured quantity.

    Within that effective horizon, the leading `inference_delay_steps` actions will
    already have been executed by the time the new chunk lands, so RTC pins them
    rather than steering them; the remainder are the softly guided actions.
    """
    for name, value in (
        ("inference_delay_steps", inference_delay_steps),
        ("overlap_actions", overlap_actions),
        ("execution_horizon", execution_horizon),
    ):
        if value < 0:
            raise ValueError(f"{name} cannot be negative")

    effective_horizon = min(execution_horizon, overlap_actions)
    frozen = min(inference_delay_steps, effective_horizon)
    return {
        "overlap_actions": overlap_actions,
        "effective_execution_horizon": effective_horizon,
        "frozen_prefix_actions": frozen,
        "guided_actions": effective_horizon - frozen,
    }


def _as_policy_tensor(policy: Any, remainder: Any) -> Any:
    """Convert the previous-chunk remainder to a tensor on the policy's device.

    `execution.py` builds the remainder with `np.stack`, but LeRobot's
    `RTCProcessor.denoise_step` calls tensor methods on it (`.unsqueeze(0)`), so a
    numpy array raises `AttributeError` mid-denoise. This never surfaced before
    `configure_rtc` was wired up: with `rtc_config=None` LeRobot accepted the
    argument and discarded it without ever touching it.

    Converting here rather than in `execution.py` keeps the runtime in numpy and
    confines LeRobot's tensor contract to this adapter.
    """
    if remainder is None:
        return None

    import torch

    if not isinstance(remainder, torch.Tensor):
        remainder = torch.as_tensor(remainder)
    try:
        device = next(policy.parameters()).device
    except (AttributeError, StopIteration):
        # Test doubles have no parameters; leave placement alone.
        return remainder.to(dtype=torch.float32)
    return remainder.to(device=device, dtype=torch.float32)


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
        prev_chunk_left_over=_as_policy_tensor(policy, previous_chunk_remainder),
        execution_horizon=execution_horizon,
    )
