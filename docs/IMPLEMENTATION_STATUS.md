# Implementation Status

Last updated: 2026-08-14

## Active stage

```text
STAGE 0 CALIBRATION FROZEN — STAGE 1 PREPARATION
```

## Existing prerequisite

Prior work indicates that a π0.5 LIBERO harness with Naive async and RTC exists. Revalidate the current repository/checkpoint/environment before using new results.

## Stage 0

- [ ] Pin LeRobot revision
- [ ] Pin π0.5 checkpoint revision
- [ ] Validate CUDA/EGL environment
- [x] Verify exact standard-LIBERO task names at IDs 2 / 0 / 2
- [x] Validate frozen `n_action_steps=25`
- [x] Validate Naive async semantics
- [x] Validate RTC semantics
- [x] Validate request-specific logical delay
- [x] Validate action-age calculation for policy actions
- [x] Record revised 180-run calibration manifest (`3 × 2 × 5 × 6`)
- [x] Run 180 revised calibration episodes
- [ ] Validate missing/invalid cells
- [ ] Generate calibration plots/tables (all four tables exist; the four required calibration plots are missing)
- [x] Write `selected_high_delay.json`
- [x] Freeze `d*=200 ms` from ID-only results under D016

### Stage 0 result snapshot

- Result bundle: `/Users/tejasrikurapati/Downloads/stage0`
- Coverage: 180/180 unique episode summaries, 180 request traces, and 180 action traces
- Matrix: 3 tasks × 2 methods × 5 delays × 6 seeds
- All episode summaries report `status=ok`; exact tasks and `fixed_horizon=25` match the frozen design
- Selection pool: four Native-viable task-method cells
- Pooled Native success: 21/24 (87.5%)
- Pooled success at Native + 200 ms: 16/24 (66.7%)
- Selected drop: 20.8 percentage points; the primary rule was satisfied without OOD results
- Validation exception: 23 hold/underrun actions in seven episodes lack canonical
  chunk/source-observation provenance, so missing/invalid-cell validation remains
  open despite all 180 episode summaries reporting `ok`

## Stage 1

- [x] Create separate LIBERO-Plus environment
- [x] Pin LIBERO-Plus SHA in the Stage 1 image
- [ ] Resolve all 21 OOD variants
- [ ] Verify `classification_id` ↔ exact task name ↔ API index
- [ ] Save `stage1_resolved_variants.csv`
- [ ] Freeze variants before outcomes
- [x] Implement deterministic 480-row Stage 1 manifest generation
- [x] Accept 24 Stage 0 controls for reuse under D018's provenance limitation
- [x] Implement manifest-driven ID/OOD runners and Stage 0 control import
- [x] Implement Stage 1 validation, seven tables, required plots, and observations
- [ ] Run 420 new OOD episodes
- [ ] Run 36 additional ID-control episodes for Stage 1 seeds 2/3/4
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
The revised Stage 0 design (`n_action_steps=25`, six seeds, 0–400 ms) and
`d*=200 ms` are frozen under D016; missing 500–700 ms cells are not a blocker.
Required repository/checkpoint/environment identity fields are still absent, so
exact matching cannot be proven. D018 nevertheless accepts the 24 seed-0/1
controls for reuse with an explicit provenance limitation. See K015-K016/K018.
Trace audit also found 23 hold/underrun actions without canonical provenance in
seven episodes despite all summaries being marked `ok`; see K017. The four
required calibration plots are also missing, although all four tables exist.
```

## Analysis artifacts

- `/Users/tejasrikurapati/Downloads/stage0/selected_high_delay.json`
- `/Users/tejasrikurapati/Downloads/stage0/STAGE_0_OBSERVATIONS.md`
- `/Users/tejasrikurapati/Downloads/stage0/table_a_per_task_calibration.csv`
- `/Users/tejasrikurapati/Downloads/stage0/table_b_pooled_curve.csv`
- `/Users/tejasrikurapati/Downloads/stage0/table_c_method_calibration.csv`
- `/Users/tejasrikurapati/Downloads/stage0/table_d_freshness.csv`
- `docs/STAGE_0_N_ACTION_STEPS_25_CONDUCT.md`

## Exact next action

```text
On the pinned A100 images, resolve and freeze the 21 LIBERO-Plus variants,
materialize the 480-row manifest, import the 24 accepted Stage 0 controls, run
the eight-episode Stage 1 smoke matrix, and validate it before dispatching the
remaining 448 new episodes.
```
