# Implementation Status

Last updated: 2026-08-09

## Active stage

```text
STAGE 0 — ID-ONLY LATENCY CALIBRATION
```

## Existing prerequisite

Prior work indicates that a π0.5 LIBERO harness with Naive async and RTC exists. Revalidate the current repository/checkpoint/environment before using new results.

## Stage 0

- [ ] Pin LeRobot revision
- [ ] Pin π0.5 checkpoint revision
- [ ] Validate CUDA/EGL environment
- [ ] Verify exact standard-LIBERO task names at IDs 2 / 0 / 2
- [ ] Validate `n_action_steps=25`
- [ ] Validate Naive async semantics
- [ ] Validate RTC semantics
- [ ] Validate request-specific logical delay
- [ ] Validate action-age calculation
- [ ] Generate 96-run calibration manifest
- [ ] Run 180 calibration episodes
- [ ] Validate missing/invalid cells
- [ ] Generate calibration plots/tables
- [ ] Write `selected_high_delay.json`
- [ ] Freeze `d*`

## Stage 1

- [ ] Create separate LIBERO-Plus environment
- [ ] Pin LIBERO-Plus SHA
- [ ] Resolve all 21 OOD variants
- [ ] Verify `classification_id` ↔ exact task name ↔ API index
- [ ] Save `stage1_resolved_variants.csv`
- [ ] Freeze variants before outcomes
- [ ] Generate 192-row Stage 1 analysis manifest
- [ ] Confirm ID controls match Stage 0
- [ ] Run 168 new OOD episodes
- [ ] Validate all factorial cells
- [ ] Generate seven required summary tables
- [ ] Generate interaction heatmaps
- [ ] Generate task-demand / mechanism-group plots
- [ ] Generate action-age diagnostics
- [ ] Write `STAGE_1_OBSERVATIONS.md`
- [ ] Apply the frozen Stage 2 selection rule

## Stage 2

- [ ] Freeze selected candidate interactions
- [ ] Freeze held-out seed set before execution
- [ ] Run held-out confirmation
- [ ] Report held-out results separately from exploratory screen
- [ ] Compute intervals/effect sizes
- [ ] Decide final paper claim
- [ ] Freeze results

## Paper

- [ ] Finalize related work
- [ ] Finalize experimental taxonomy language
- [ ] Generate main figures from scripts
- [ ] Include complete Stage 1 screen
- [ ] Include null/counterintuitive results
- [ ] Audit every claim against a result
- [ ] Write limitations
- [ ] Reproducibility audit
- [ ] Final manuscript

## Current blockers

Record only concrete blockers here.

```text
None recorded in this specification.
```

## Exact next action

```text
Run the Stage 0 preflight assertions and generate the 96-episode latency-calibration manifest.
```
