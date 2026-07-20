# Days 1–3 Implementation Status

Last updated: 2026-07-21

Current state: benchmark infrastructure and scripts are implemented, but real
experimental execution has not been performed. The checks below validate local
scaffolding and are not evidence of completed experiments.

## Scope

- [x] Scope limited to ideal synchronous, blocking synchronous, naive asynchronous queue, RTC, and fixed execution horizons.
- [x] No policy training, OOD perturbations, dynamic interventions, VLASH, FASTER, DEHP, SmolVLA, or OpenVLA.

## Inspection and environment

- [x] Read `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and `docs/DAYS_1_3_SPEC.md` completely.
- [x] Inspected workspace and all discovered Python environments.
- [x] Inspected current upstream LeRobot π0.5, RTC, and LIBERO APIs as a scaffolding reference.
- [ ] Pin local LeRobot Git commit (blocked: no LeRobot checkout or installation).
- [ ] Pin checkpoint and dataset revision SHAs (blocked: artifacts not installed/downloaded).
- [ ] Validate Linux/CUDA/EGL execution environment (blocked: current host is macOS without CUDA stack).

## Implementation

- [x] Create isolated benchmark package structure.
- [x] Implement latency conversion, provenance, queue, logical clock, RTC call adapter, metrics, and guarded environment/policy adapters.
- [x] Complete production episode execution and output logging.
- [x] Implement inspect_setup, task selection, profiling, benchmark, validation, figure, and test-runner scripts.
- [x] Implement latency, action-age, naive-queue, horizon, RTC, and reproducibility tests.
- [x] Add `--output-dir` overrides to all CLI scripts for Modal volume mounting.
- [x] Create `modal_app.py`, `Dockerfile.modal`, and `docs/MODAL.md` for remote GPU execution.

## Validation and experiments

### Implementation-only checks

- [x] Dependency-free latency smoke test passes (`0/1/100/101/300/700 ms`).
- [x] Package syntax compilation passes under Python 3.14.5.
- [x] Core dry-run expands to 150 episodes; horizon dry-run expands to 108 maximum episodes.
- [x] Custom test runner passes 6/7 tests (1 skipped because LeRobot/LIBERO is not installed).

### Experimental completion criteria

- [ ] Execution environment metadata captured from the required Linux/CUDA/EGL host.
- [ ] Exact checkpoint loads on CUDA.
- [ ] Three viable tasks selected.
- [ ] 100 measured native requests profiled.
- [ ] Core episode logs validated.
- [ ] RTC verified with request-specific delays.
- [ ] Horizon sweep logs validated.
- [ ] Figures generated after validation.

Experimental completion: **not achieved**. No validated request, action, episode,
task-selection, native-latency, horizon-sweep, summary, or figure artifacts exist on
this host.

## Recorded deviations and failures

- 2026-07-21: Workspace is a Git repository; LeRobot and LIBERO are not installed.
- 2026-07-21: No CUDA runtime/GPU is available on the macOS development host.
- 2026-07-21: Artifact revisions (`checkpoint_revision`, `dataset_revision`) are still `null` in `configs/days1_3.yaml`.
- 2026-07-21: No benchmark episodes have been executed; all outputs are scaffolding diagnostics.
- 2026-07-21: `pytest` is not installed, but `scripts/run_tests.py` provides a shim and runs the test suite.
- 2026-07-21: `inspect_setup.py` writes `async_vla_benchmark/outputs/environment.json` with `status: not_ready`.
