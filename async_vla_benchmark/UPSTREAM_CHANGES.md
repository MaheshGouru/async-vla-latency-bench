# Upstream Changes

No LeRobot core files have been modified. The benchmark uses isolated adapters.

This file records LeRobot behaviours that the adapters must work around, as required by
`docs/DAYS_1_3_SPEC.md` section 4. All observations are against the pinned commit
`2aba372b4e217cc47db28e0f836859b20d1456c9` (lerobot 0.6.1).

## 1. RTC is inert unless `rtc_config` is set explicitly

`PI05Config.rtc_config` defaults to `None`, and the `lerobot/pi05_libero_finetuned`
checkpoint ships `null`. With it unset, `policy._rtc_enabled()` returns `False` and
`euler_integrate` receives `rtc_enabled=False`, so the `inference_delay`,
`prev_chunk_left_over`, and `execution_horizon` arguments are **accepted and silently
discarded** — no error, no warning, and no RTC guidance.

*Workaround:* `benchmark/rtc.py::configure_rtc` assigns an `RTCConfig` and calls
`policy.init_rtc_processor()`, then asserts a live `rtc_processor` rather than trusting
the assignment. `scripts/run_benchmark.py` calls it at policy load.

*Why it matters:* this silently invalidated an entire RTC arm (81 episodes) before it was
caught. Any harness passing RTC arguments should assert `policy.rtc_processor is not None`
rather than assuming the arguments took effect.

## 2. `prev_chunk_left_over` must be a torch tensor, not an array

`lerobot/policies/rtc/modeling_rtc.py::RTCProcessor.denoise_step` calls
`prev_chunk_left_over.unsqueeze(0)`. A numpy array raises `AttributeError` mid-denoise.
The argument is untyped and undocumented in this respect, and — because of item 1 — the
mismatch is invisible until guidance is actually enabled.

*Workaround:* `benchmark/rtc.py::_as_policy_tensor` converts the remainder to a float32
tensor on the policy's device at the adapter boundary, keeping the runtime in numpy.

## 3. `execution_horizon` is silently clamped to the remainder length

LeRobot reduces the effective `execution_horizon` to `len(prev_chunk_left_over)` when the
queue remainder is shorter than the configured horizon. With
`request_threshold_actions = ceil(h/2)`, the remainder is at most `ceil(h/2)`, so the
horizon in force is always at most half the configured value. Measured in this benchmark:
**4.67 against a configured 10.**

*Workaround:* not corrected — corrections would change RTC's semantics. Instead
`benchmark/rtc.py::rtc_action_counts` computes and records the effective horizon per
request, so the clamp is a measured quantity rather than a hidden one.

## 4. Flow-matching noise is drawn from the unseeded global RNG

`lerobot/policies/common/flow_matching.py::sample_noise` draws from PyTorch's global RNG.
Two runs of an identical `(task, strategy, profile, horizon, seed)` condition therefore
diverge after `env.reset`, despite deterministic environment initialisation.

*Workaround:* `EpisodeRunner.run()` calls `torch.manual_seed(seed)` per episode. This
reduced cross-run disagreement from 5.6-8.3% to ~2.8%; the residual is attributed to
GPU/cuDNN floating-point non-determinism and is **not** eliminated.

## 5. RTC's `inference_delay` cannot be satisfied as specified

Section 15 requires the runtime `inference_delay` to reflect the current request's
measured latency, but that latency is not knowable until the request it parameterises has
returned.

*Workaround:* `benchmark/latency.py::estimate_inference_delay_steps` uses the most recent
measured request in the episode — one request-specific observation rather than the global
average the spec forbids. The residual error is logged per request
(`rtc_inference_delay_error_steps`); measured mismatch rate is **37%**, mean absolute
error 1.75 steps.
