# Async VLA Benchmark: Days 1–3

This isolated package implements the π0.5–LIBERO latency benchmark specified in
`docs/DAYS_1_3_SPEC.md`. It does not train a policy or implement deferred methods such
as VLASH, FASTER, DEHP, SmolVLA, or OpenVLA.

## What is implemented

- Discrete-event episode execution for the four baseline strategies:
  `ideal_sync`, `blocking_sync`, `naive_async`, and `rtc`.
- Latency-to-delay-step conversion using `ceil` and request-specific measured latency.
- Action provenance tracking across observations, chunks, requests, and executed actions.
- Guarded LeRobot/LIBERO adapters and control-frequency resolution.
- Policy loading, preprocessor/postprocessor loading, and a timed `predict_action_chunk`
  wrapper with CUDA synchronization.
- Output writers for requests, actions, episode summaries, CSV tables, and JSON artifacts.
- CLI entry points for environment inspection, task selection, native latency profiling,
  benchmark execution, result validation, and figure generation.
- A custom test runner that runs the test suite without `pytest`.

## Requirements

Real experiments require a Linux host with:

- A pinned LeRobot Git checkout (`pip install -e .[pi,libero]` or equivalent).
- `mujoco`, `robosuite`, and `libero` installed.
- A CUDA-capable GPU with working EGL rendering.
- Pinned checkpoint and dataset revisions in `configs/days1_3.yaml`.

## Quickstart

1. Inspect the environment:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/inspect_setup.py
```

2. Pin revisions in `async_vla_benchmark/configs/days1_3.yaml`.

3. Select one viable task per suite:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/select_tasks.py \
  --config async_vla_benchmark/configs/days1_3.yaml
```

4. Profile native request latency:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/profile_latency.py \
  --config async_vla_benchmark/configs/days1_3.yaml
```

5. Run the core benchmark:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/run_benchmark.py \
  --config async_vla_benchmark/configs/days1_3.yaml --experiment core
```

6. Validate and make figures:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/validate_results.py \
  --output-dir async_vla_benchmark/outputs
PYTHONPATH=. python async_vla_benchmark/scripts/make_figures.py \
  --output-dir async_vla_benchmark/outputs
```

## Dry-run and tests

The package can be exercised locally without LeRobot or CUDA:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/run_tests.py
PYTHONPATH=. python async_vla_benchmark/scripts/run_benchmark.py \
  --config async_vla_benchmark/configs/days1_3.yaml --experiment core --dry-run \
  --task libero_spatial:0 --task libero_goal:0
```

## Current environment status

The macOS development host used for this workspace does not have `lerobot`, `libero`,
`mujoco`, `robosuite`, CUDA, or `pytest`. The code has been compiled and the unit-style
checks pass, but no benchmark episodes have been executed on a real π0.5 checkpoint.
