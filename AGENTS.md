# Async VLA Benchmark Instructions

Before making changes, read these files completely:

1. `docs/RESEARCH_CONTEXT.md`
2. `docs/DAYS_1_3_SPEC.md`

## Current objective

Implement only the Days 1–3 π0.5-LIBERO latency benchmark.

Required execution conditions:

- Ideal synchronous
- Blocking synchronous
- Naive asynchronous queue
- RTC
- Fixed execution-horizon sweep

Do not implement VLASH, FASTER, DEHP, SmolVLA, OpenVLA, OOD
perturbations, dynamic interventions, or policy training yet.

## Working rules

- Inspect the current LeRobot APIs before writing adapters.
- Do not assume that documentation matches the installed revision.
- Prefer an isolated benchmark package over modifying LeRobot internals.
- Pin repository, checkpoint, and environment revisions.
- Use request-specific measured latency.
- Use a discrete-event simulator; do not use `sleep()` to inject delay.
- Track every action's source observation and source chunk.
- Run tests and validate logs before producing figures.
- Do not claim an experiment completed when it was only implemented.
- Record failures and deviations explicitly.