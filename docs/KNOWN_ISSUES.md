# Known Issues

Last updated: 2026-07-21

## Blocking experimental execution

1. **No pinned LeRobot checkout or installation.** `lerobot` is not importable on the
   macOS development host and no LeRobot commit can currently be recorded.
2. **Required simulation packages are absent.** `libero`, `mujoco`, and `robosuite` are
   not installed.
3. **No CUDA/EGL execution host.** The current machine is macOS and has no available CUDA
   runtime or GPU. It cannot satisfy the required Linux/CUDA/EGL conditions.
4. **Artifact revisions are unresolved.** The checkpoint and dataset revision SHAs are
   still `null` in `configs/days1_3.yaml`.
5. **Control frequency resolution is unvalidated.** `environment.resolve_control_frequency_hz`
   now walks wrappers and checks `metadata["render_fps"]`, but it has not been verified
   against an instantiated `LiberoEnv`.

## Implementation status

The core benchmark package is implemented. The remaining risks are:

1. The LeRobot preprocessor input format for the LIBERO `pixels`/`robot_state` observation
   dict has been inferred from upstream source but not validated against a pinned installed
   revision or checkpoint.
2. The RTC wrapper passes `inference_delay`, `prev_chunk_left_over`, and `execution_horizon`
   but has not been exercised against a real π0.5 checkpoint.
3. Parquet output schemas and the result validator have not been exercised on real
   benchmark episodes.
4. `make_figures.py` requires `matplotlib` and validated summaries.

## Test status

1. `pytest` is not installed. `scripts/run_tests.py` injects a minimal pytest shim and runs
   the test suite; 6/7 tests pass and 1 is skipped because LeRobot/LIBERO is missing.
2. Implementation checks (latency, queue, action age, horizon, RTC) pass, but they do not
   exercise LeRobot, LIBERO, CUDA timing, or environment rollouts.

## Output status

1. `async_vla_benchmark/outputs/environment.json` is a failed-readiness diagnostic with
   `status: not_ready`.
2. No validated experimental request, action, episode, task-selection, latency-profile,
   summary, report, or figure artifacts exist on this host.
3. No task has been selected, no checkpoint has loaded, and zero benchmark episodes have
   been run.
