# Days 1–3 Implementation Status

Last updated: 2026-07-20

Current state: implementation is partial and experimental execution has not started.
The smoke test, syntax check, and dry-run matrix checks validate only local scaffolding;
they are not benchmark episodes and do not satisfy any experimental completion criterion.

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
- [ ] Complete production episode execution and output logging.
- [ ] Implement setup, task selection, profiling, benchmark, validation, and figure scripts.
- [x] Implement initial latency, action-age, naive-queue, horizon, and RTC tests.

## Validation and experiments

### Implementation-only checks

- [x] Dependency-free latency smoke test passes (`0/1/100/101/300/700 ms`).
- [x] Package syntax compilation passes under Python 3.10.18.
- [x] Core dry-run expands to 150 episodes; horizon dry-run expands to 108 maximum episodes.
- [ ] Full pytest suite passes (blocked: pytest is not installed on this host).

### Experimental completion criteria

- [ ] Execution environment metadata captured from the required Linux/CUDA/EGL host.
- [ ] Exact checkpoint loads on CUDA.
- [ ] Three viable tasks selected.
- [ ] 100 measured native requests profiled.
- [ ] Core episode logs validated.
- [ ] RTC verified with request-specific delays.
- [ ] Horizon sweep logs validated.
- [ ] Figures generated after validation.

Experimental completion: **not achieved**. There are no validated request, action,
episode, task-selection, native-latency, horizon-sweep, summary, or figure artifacts.

## Recorded deviations and failures

- 2026-07-20: Workspace contained only instructions and was not a Git repository.
- 2026-07-20: No installed `lerobot`, `libero`, `mujoco`, or `robosuite` package was found.
- 2026-07-20: No CUDA runtime/GPU is available on the macOS development host.
- 2026-07-20: No experiments have been run and no experimental output is claimed.
- 2026-07-20: Initial pytest invocation failed because pytest is not installed in the discovered Python 3.10 environment.
- 2026-07-20: `inspect_setup.py` wrote `outputs/environment.json` with `status: not_ready`; this is a setup diagnostic, not evidence of an experiment run.
- 2026-07-20: Work stopped with production episode execution, logging, result validation, and figure generation still incomplete.
