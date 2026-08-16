# Async VLA Benchmark Instructions

Before making changes, read these files completely:

1. `docs/RESEARCH_CONTEXT.md`
2. `docs/STAGE_1_EXPLORATORY_SCREEN.md`
3. `docs/METRICS_AND_LOGGING.md`

## Current objective

Implement the Stage 1 π0.5 LIBERO-Plus exploratory OOD × inference-delay screen.

Required Stage 1 execution conditions:

- frozen `policy.n_action_steps=25`
- frozen ID-calibrated `d*=200 ms`
- Native and Native + `d*`
- Naive asynchronous queue and RTC
- three frozen base tasks and all seven LIBERO-Plus perturbation families
- five Stage 1 seeds: `0, 1, 2, 3, 4`
- 420 OOD episodes plus 60 shared ID controls

Reuse the 24 Stage 0 ID controls for seeds `0` and `1` without rerunning them,
as an explicitly recorded provenance limitation. Run the 36 missing ID controls
for seeds `2`, `3`, and `4`.

Do not implement VLASH, FASTER, DEHP, SmolVLA, OpenVLA, dynamic interventions,
additional models, or policy training.

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
