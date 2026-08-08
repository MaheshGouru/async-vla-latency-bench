#!/usr/bin/env python3
"""Report whether RTC guidance is actually active on the loaded policy.

Answers two questions against real LeRobot, which unit tests with fakes cannot:

1. Did the Days 1-3 runs have RTC guidance? `load_pi05_policy` is what those
   runs used, and nothing else touched `config.rtc_config`. If the policy comes
   back with `rtc_config=None`, then `_rtc_enabled()` was False and
   `euler_integrate` took its unguided branch -- the per-request
   inference_delay/prev_chunk_left_over/execution_horizon arguments were
   forwarded but never applied.

2. Does `configure_rtc` actually activate guidance against the installed API?

Run via `modal run modal_app.py --command diagnose_rtc`.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _probe(policy) -> dict:
    """Snapshot the policy's RTC state using LeRobot's own predicates."""
    rtc_config = getattr(policy.config, "rtc_config", "<attribute missing>")
    state = {
        "config.rtc_config": repr(rtc_config),
        "policy.rtc_processor": repr(getattr(policy, "rtc_processor", "<attribute missing>")),
    }
    # _rtc_enabled is the exact gate euler_integrate receives as rtc_enabled.
    enabled = getattr(policy, "_rtc_enabled", None)
    state["policy._rtc_enabled()"] = enabled() if callable(enabled) else "<method missing>"
    if rtc_config not in (None, "<attribute missing>"):
        for field in ("enabled", "prefix_attention_schedule", "max_guidance_weight", "execution_horizon"):
            state[f"rtc_config.{field}"] = repr(getattr(rtc_config, field, "<missing>"))
    return state


def main(config_path: Path | None = None) -> int:
    from async_vla_benchmark.benchmark.config import load_config
    from async_vla_benchmark.benchmark.policy import load_pi05_policy
    from async_vla_benchmark.benchmark.rtc import build_rtc_config, configure_rtc

    cfg = load_config(config_path or ROOT / "configs" / "days1_3.yaml")
    policy = load_pi05_policy(
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
        n_action_steps=cfg.policy_n_action_steps,
        device=cfg.device,
    )

    before = _probe(policy)
    print("\n=== AS THE DAYS 1-3 RUNS LOADED IT (pre-fix behavior) ===")
    print(json.dumps(before, indent=2))

    configure_rtc(
        policy,
        build_rtc_config(
            execution_horizon=cfg.rtc.execution_horizon,
            max_guidance_weight=cfg.rtc.max_guidance_weight,
            prefix_attention_schedule=cfg.rtc.prefix_attention_schedule,
        ),
    )
    after = _probe(policy)
    print("\n=== AFTER configure_rtc (post-fix behavior) ===")
    print(json.dumps(after, indent=2))

    guidance_was_off = before.get("policy._rtc_enabled()") is False
    guidance_now_on = after.get("policy._rtc_enabled()") is True
    print("\n=== VERDICT ===")
    print(f"Days 1-3 runs had RTC guidance active: {not guidance_was_off}")
    print(f"configure_rtc activates guidance:      {guidance_now_on}")
    if not guidance_now_on:
        print("FAIL: configure_rtc did not activate guidance against the installed API")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.config))
