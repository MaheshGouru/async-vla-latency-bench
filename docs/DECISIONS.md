# Decisions

Last updated: 2026-07-20

## Scope and architecture

1. Keep all benchmark work in the isolated `async_vla_benchmark/` package.
   LeRobot core files will not be modified unless a pinned installed revision makes
   an upstream change unavoidable.
2. Implement only the Days 1–3 conditions: ideal synchronous, blocking synchronous,
   naive asynchronous queue, RTC, and the fixed execution-horizon sweep.
3. Use a discrete-event logical clock. Added latency will never be implemented with
   `sleep()` or real-time pacing.
4. Permit at most one outstanding policy request and retain observation/chunk/action
   provenance through every queue operation.

## Dependency and revision handling

1. Current upstream LeRobot source may guide scaffolding, but it is not treated as the
   installed experimental revision. Experimental adapters must be checked again against
   the pinned local checkout.
2. Repository, checkpoint, and dataset revisions must be explicit before real execution.
   Missing revisions cause an actionable failure rather than an implicit latest-version
   lookup.
3. The environment control frequency must be obtained from the pinned environment.
   The benchmark will not silently assume a frequency.
4. Real policy loading requires CUDA. The present macOS host is suitable only for
   dependency-free implementation checks and dry-run planning.

## Latency and RTC semantics

1. Convert each request's measured end-to-end latency to logical delay with `ceil`.
   A global average latency is not valid for RTC or other execution strategies.
2. Define action age from the source observation control step, not policy completion
   time.
3. Pass `inference_delay`, `prev_chunk_left_over`, and `execution_horizon` through the
   current RTC-capable π0.5 chunk path. Add a pinned-revision regression test before RTC
   experiments.
4. Treat the initial queue fill as ideal startup or record it separately; it must not be
   silently mixed into steady-state latency measurements.

## Evidence and reporting

1. Smoke tests, compilation, and dry runs are implementation evidence only.
2. An experiment is complete only when its required output exists and passes result
   validation.
3. Aggregate figures must not be generated until validation passes.
4. The diagnostic `outputs/environment.json` currently has `status: not_ready` and is
   not an experimental result.
