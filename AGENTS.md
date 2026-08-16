# Async VLA Benchmark Instructions

Before making changes, read these files completely:

1. `docs/RESEARCH_CONTEXT.md`
2. `docs/STAGE_1_EXPLORATORY_SCREEN.md`
3. `docs/METRICS_AND_LOGGING.md`

## Current objective

Implement the frozen Stage 3 held-out OOD confirmation without modifying Stage 0
or Stage 1 artifacts.

Required Stage 3 execution conditions:

- RTC only
- `n_action_steps = {20,25,30}`
- Native and Native + 200 ms
- held-out seeds `14..21`
- exact Stage 1 OOD variants frozen in `STAGE_3_OOD_HORIZON_CONFIRMATION.md`
- 96 logically shared ID controls and 192 OOD episodes
- sensor noise labeled only as `posthoc_replication`
- strict initialization pairing across the six horizon/delay cells for each
  `(task, variant, seed, scene)` key

Stage 2 is supporting sensitivity evidence only. It must not alter the frozen
Stage 3 horizons, delays, seeds, or exact Stage 1 OOD variant identities. Surface
documentation inconsistencies for review rather than changing the experiment.

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
