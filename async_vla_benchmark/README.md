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

6. Validate, aggregate, and make figures:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/validate_results.py \
  --output-dir async_vla_benchmark/outputs
PYTHONPATH=. python async_vla_benchmark/scripts/aggregate_results.py \
  --config async_vla_benchmark/configs/days1_3.yaml \
  --output-dir async_vla_benchmark/outputs
PYTHONPATH=. python async_vla_benchmark/scripts/make_figures.py \
  --output-dir async_vla_benchmark/outputs
```

`aggregate_results.py` rebuilds `summaries/{episodes,requests,horizon_sweep}.csv` from the
per-episode artifacts, which are authoritative. Run it after any partial or sharded run:
`run_benchmark.py` merges into the aggregate JSONs at the end of a run, so two concurrent
jobs can interleave their read-modify-write and drop each other's rows. Rebuilding from
`episodes/` and `requests/` recovers the full set regardless of how runs were sharded.

## Dry-run and tests

The package can be exercised locally without LeRobot or CUDA:

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/run_tests.py
PYTHONPATH=. python async_vla_benchmark/scripts/run_benchmark.py \
  --config async_vla_benchmark/configs/days1_3.yaml --experiment core --dry-run \
  --task libero_spatial:0 --task libero_goal:0
```

## Running on Modal

A complete Modal deployment is included for remote GPU execution. See `docs/MODAL.md`
for setup, deploy, and run instructions.

**Always pass `--detach`:**

```bash
modal run --detach modal_app.py::main --command run --experiment all
```

`modal run` without `--detach` creates an ephemeral app that Modal stops when the local
client disconnects, and it takes `.spawn()`ed calls down with it — the run dies after the
image build with `Stopping app - local client disconnected`, having executed nothing.

Outputs land on the Modal volume `async-vla-benchmark-outputs`, not in this directory.
Retrieve them with `modal volume get` before aggregating or plotting locally.

## Results

Days 1-3 results and the section 24 answers are in
`outputs/summaries/days1_3_report.md`; the harness audit is in
`outputs/summaries/days1_3_audit.md`. LeRobot behaviours the adapters work around are
recorded in `UPSTREAM_CHANGES.md`.

Headline: at 20 Hz, native inference occupies **11 control steps** against the core
experiment's **10**-step horizon, so every asynchronous strategy operates outside its
design regime. `blocking_sync` (0.933 success at native latency) outperforms
`naive_async` (0.267) and `rtc` (0.067). RTC contributes **zero guided actions** at every
horizon tested while improving action continuity by 24-29%.

## Current environment status

Full Days 1-3 execution completed 2026-08-08 on Modal (A100-40GB): 222 unique episodes,
3998 requests, `validate_results.py` clean. The local development host has no `lerobot`,
`libero`, `mujoco`, `robosuite`, CUDA, or `torch`; the test suite runs there with
torch-dependent cases skipped, so RTC tensor-contract tests execute only in the container.
