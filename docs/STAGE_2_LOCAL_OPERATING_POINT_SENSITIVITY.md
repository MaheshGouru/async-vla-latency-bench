# Stage 2 — Local Operating-Point Sensitivity

## 0. Purpose

**Highest-priority next experiment.**

Stage 0 and Stage 1 are complete and must not be retroactively changed.

The frozen Stage 1 operating point was:

```text
RTC n_action_steps = 25
high added delay = +200 ms
```

Stage 2 does **not** search for a new optimum. Its purpose is narrower:

> **Is the already-used `(25 actions, +200 ms)` operating point locally stable, or
> is it a knife-edge configuration whose conclusions would change under small,
> reasonable changes to action coverage or delay?**

The Stage 1 results remain analyzed at 25/+200 regardless of Stage 2 outcome.

## 1. Why these action-coverage values?

Use:

```text
n_action_steps ∈ {10, 15, 20, 25, 30, 35}
```

Rationale:

- `25` is the frozen Stage 1 configuration.
- `20` and `30` are the nearest ±5-action perturbations around 25.
- `15` and `35` extend the local window to ±10 actions and test whether the trend
  persists rather than depending only on the nearest neighbors.
- `10` is retained as a **diagnostic anchor** because the project already observed
  qualitatively brittle RTC behavior at this setting.
- Values above 35 are not required for this sensitivity study because the goal is
  not global horizon optimization.
- Values below 10 are not required because 10 already supplies the known
  short-coverage failure anchor.

Do not call 25 the "best" or "optimal" horizon. Call it the **calibrated Stage 1
operating point**.

## 2. Why these delay values?

Use:

```text
added_delay_ms ∈ {0, 100, 200, 300}
```

Rationale:

- `200 ms` is the frozen Stage 1 high-delay condition.
- `100 ms` is a one-step local perturbation below it.
- `300 ms` is a one-step local perturbation above it.
- `0 ms` / Native is included as a **same-seed baseline at every tested
  `n_action_steps`**. Completed Stage 0/1 do not provide Native controls for all
  of `15,20,30,35`, so omitting Native would confound:
  - a horizon being intrinsically weak even without added delay; and
  - that horizon being specifically more sensitive to injected delay.
- The 0/100/200/300-ms window remains local around the frozen +200-ms operating
  point and does not repeat the earlier broad latency calibration.

This experiment is therefore a **local operating-point sensitivity check**, not a
new latency calibration or global horizon optimization.

## 3. Fixed model, tasks, and method

```text
model = lerobot/pi05_libero_finetuned

tasks =
    libero_spatial:2
    libero_goal:0
    libero_10:2

primary method = RTC
```

Run RTC only in the required Stage 2 matrix. Naive async is not needed to defend
the RTC operating point and would substantially increase compute.

## 4. Frozen Stage 2 seeds

Use exactly:

```text
SEEDS = [5, 6, 7, 8, 9]
```

Why these seeds:

- Stage 1 used `[0,1,2,3,4]`.
- Revised Stage 0 additionally used `[10,11,12,13]` together with `0,1`.
- `[5,6,7,8,9]` are therefore a clean five-seed set not used by completed Stage 0
  or Stage 1.
- The same five seeds must be used in **every Stage 2 condition**.
- Do not replace individual failed seeds or choose seed values by task/horizon.
- A rerun of an invalid episode must reuse the same seed and be marked as a
  replacement, not a new replicate.

Manifest assertion:

```python
SEEDS = [5, 6, 7, 8, 9]
assert sorted(set(row["seed"] for row in stage2_rows)) == SEEDS
```

## 5. Run matrix

```text
6 n_action_steps values
× 4 delay values [Native, +100, +200, +300 ms]
× 3 ID tasks
× 5 fixed seeds
× 1 method [RTC]
= 360 episodes
```

This is the complete required Stage 2 matrix.

The additional 90 Native episodes are required to separate the **main effect of
action coverage** from **sensitivity to added delay** at each action-coverage
setting.

## 5A. Episode-level pairing

The completed Stage 0 result table used seeds:

```text
[0,1,10,11,12,13]
```

Stage 2 intentionally uses the independent block:

```text
[5,6,7,8,9]
```

Do not reuse Stage 0 rows as Stage 2 replicates.

For every fixed `(task_key, seed)`, all 24 Stage 2 configurations:

```text
6 n_action_steps × 4 delays
```

must use the same seeded base-task initialization.

Required manifest identity fields:

```text
task_key
suite
task_id
task_name
seed
initialization_index_or_id
initial_state_fingerprint
```

The sensitivity comparison is paired **within Stage 2**, not by recycling Stage
0/1 episode seeds.

See `EPISODE_MATCHING_AND_VARIANT_FREEZE.md`.

## 6. Preflight implementation audit

Before dispatch:

1. Confirm `n_action_steps` is the only intended configuration change across
   action-coverage cells.
2. Record the checkpoint's prediction horizon.
3. Audit how `n_action_steps` maps to RTC's committed/frozen/guided/fresh action
   regions.
4. Do **not** equate `n_action_steps` with the RTC paper's formal execution horizon
   `s` unless implementation inspection proves equivalence.
5. Verify request-specific delay is passed into RTC.
6. Verify logical delay uses:
   ```text
   ceil(total_logical_latency_ms / control_period_ms)
   ```
7. Log actual measured request latency for every request.

## 7. Required logging

In addition to canonical fields:

```text
configured_n_action_steps
prediction_horizon_actions
control_period_ms
measured_request_latency_ms
added_delay_ms
total_logical_latency_ms
logical_delay_steps

coverage_ratio_added
coverage_ratio_total

rtc_frozen_prefix_steps
rtc_guided_overlap_steps
rtc_fresh_suffix_steps
previous_chunk_remaining_at_request
previous_chunk_remaining_at_response
```

Definitions:

```text
coverage_ratio_added =
    added_delay_steps / configured_n_action_steps

coverage_ratio_total =
    total_logical_delay_steps / configured_n_action_steps
```

## 8. Primary analysis

### A. Local success surface

For each task, tabulate/plot:

```text
rows = n_action_steps [10,15,20,25,30,35]
columns = delay [Native,100,200,300]
cell = success / 5
```

### B. Local stability around the frozen point

The immediate neighborhood is:

```text
n_action_steps ∈ {20,25,30}
delay ∈ {Native,100,200,300}
```

Do not define stability as "25 has the highest success."

Instead ask whether:

1. `25/+200` is not an isolated successful cell surrounded by failure;
2. the qualitative RTC behavior is similar at nearby 20/25/30 coverage;
3. ±100 ms around +200 does not completely reverse the conclusion;
4. nearby configurations remain in the same broad success regime.

### C. Baseline-normalized delay sensitivity

For every `n_action_steps = h`, compute:

```text
Δ100(h) = S(h,+100) - S(h,Native)
Δ200(h) = S(h,+200) - S(h,Native)
Δ300(h) = S(h,+300) - S(h,Native)
```

This distinguishes the **horizon main effect** `S(h,Native)` from the incremental
effect of added delay `S(h,+d) - S(h,Native)`.

This separation is required for defending both parts of the Stage 1 operating
point: `n_action_steps=25` and `d*=+200 ms`.

### D. Diagnostic 10-action anchor

Use `10` only to show whether the previously observed brittle regime persists
under the same current runner/configuration.

Do not use the 10-action result to reselect Stage 1 parameters.

### E. Descriptive normalized coverage

Plot success against:

```text
total_logical_delay_steps / configured_n_action_steps
```

as secondary analysis.

Do not claim this ratio is a universal law.

## 9. Decision rule after Stage 2

Stage 1 remains unchanged regardless of the result.

Classify the frozen 25/+200 point as:

### Locally stable

when the Native baselines at 20/25/30 are not qualitatively incompatible, the
delay-induced drops around +200 ms are broadly consistent across the local
20/25/30 neighborhood, and 25/+200 is not an isolated peak.

### Locally sensitive

when small neighboring changes produce large qualitative reversals.

### Potentially under-covered

when success continues to improve strongly and monotonically through 30 and 35
at +200 ms.

If the last case occurs, report it as a limitation of Stage 1. Do **not** rerun the
entire Stage 1 screen at a retrospectively better horizon and present that as the
original experiment.

## 10. Required outputs

```text
stage2_local_sensitivity_manifest.csv
stage2_local_sensitivity_episode_results.csv
stage2_local_sensitivity_summary.csv
stage2_local_neighborhood.csv
stage2_native_baseline_by_horizon.csv
stage2_delay_drop_from_native.csv

stage2_local_surface_spatial.png
stage2_local_surface_goal.png
stage2_local_surface_long.png
stage2_horizon_slice_200ms.png
stage2_delay_slice_25actions.png
stage2_normalized_coverage.png

STAGE_2_LOCAL_SENSITIVITY_OBSERVATIONS.md
```

## 11. Paper wording

If stable:

> "The Stage 1 operating point was selected using ID-only calibration before OOD
> evaluation. A subsequent local sensitivity analysis over 10–35 configured
> actions and ±100 ms around the selected +200 ms delay showed that the chosen
> 25/+200 setting lies within a stable operating region rather than at an isolated
> optimum."

If sensitive:

> "A post-hoc local sensitivity analysis showed substantial dependence on action
> coverage around the Stage 1 operating point; we therefore treat the Stage 1
> results as specific to the frozen 25-action configuration."
