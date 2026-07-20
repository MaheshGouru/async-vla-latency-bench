# Known Issues

Last updated: 2026-07-20

## Blocking experimental execution

1. **No pinned LeRobot checkout or installation.** The workspace is not a Git repository,
   `lerobot` is not importable, and no LeRobot commit can currently be recorded.
2. **Required simulation packages are absent.** `libero`, `mujoco`, and `robosuite` are
   not installed in the discovered Python environments.
3. **No CUDA/EGL execution host.** The current machine is macOS and has no available CUDA
   runtime or GPU. It cannot satisfy the required Linux/CUDA/EGL conditions.
4. **Artifact revisions are unresolved.** The checkpoint and dataset revision SHAs have
   not been resolved or pinned.
5. **Control frequency is unresolved.** It cannot be measured from environment metadata
   until the pinned LIBERO environment is installed and instantiated.

## Incomplete implementation

1. Production environment rollout and policy preprocessing/postprocessing integration are
   not implemented.
2. Task selection, native latency profiling, complete episode logging, resume validation,
   and figure generation scripts are not complete.
3. The result validator does not yet implement all failure conditions from the specification.
4. The current RTC wrapper is based on upstream source inspection and has not been verified
   against a pinned installed LeRobot revision or a real π0.5 checkpoint.
5. Parquet output dependencies and schemas have not been exercised.

## Test limitations

1. `pytest` is missing from the available Python 3.10 environment, so the full test suite
   has not run.
2. The latency smoke test passed, package compilation passed, and dry-run counts matched
   the specified matrices. These checks do not exercise LeRobot, LIBERO, CUDA timing, RTC
   denoising, environment actions, or output validation.

## Output status

1. `async_vla_benchmark/outputs/environment.json` is a failed-readiness diagnostic with
   `status: not_ready`.
2. No validated experimental request, action, episode, task-selection, latency-profile,
   summary, report, or figure files exist.
3. No task has been selected, no checkpoint has loaded, and zero benchmark episodes have
   been run.
