# Stage 3 — Held-Out OOD Confirmation Around the Operating Regime

## 0. Purpose

Run only after Stage 2.

Stage 3 tests whether the localized Stage 1 OOD interactions reproduce on held-out
seeds and whether the result is sensitive to reasonable action-coverage changes.

Stage 0 and Stage 1 remain unchanged.

## 1. Frozen Stage 3 seeds

Use exactly:

```text
SEEDS = [14, 15, 16, 17, 18, 19, 20, 21]
```

Why these seeds:

- disjoint from Stage 1 `[0..4]`;
- disjoint from Stage 2 `[5..9]`;
- disjoint from revised Stage 0's additional `[10..13]`;
- eight held-out replicates provide substantially finer success resolution than
  Stage 1's five exploratory seeds.

Use the **same eight seeds for every Stage 3 condition**.

Do not:
- swap a seed because it fails;
- use different seeds for different perturbations;
- count Stage 1 seeds as confirmatory replicates.

Invalid episodes may be rerun only with the same seed.

Manifest assertion:

```python
SEEDS = [14,15,16,17,18,19,20,21]
assert sorted(set(row["seed"] for row in stage3_rows)) == SEEDS
```

## 2. Prespecified OOD candidates

Carry all three tied Stage 1 family-level candidates:

```text
Long stove/moka × Object layout
Goal drawer × Robot initial state
Goal drawer × Lighting
```

These are the primary held-out confirmations.

The task/method resolution applies the frozen Stage 1 eligibility guard before
ranking localized cells: the supporting RTC subset must have ID-low success at
or above 50%. This excludes negative interactions attributable only to Naive
async floor cells. Under that guard, the listed task pairs are the eligible RTC
follow-ups for the three tied families.

Secondary post-hoc replication:

```text
Goal drawer × Sensor noise
```

Sensor noise must remain labeled post-hoc because it did not pass the original
family-level selection rule.

## 3. Delay

Keep the completed Stage 1 comparison:

```text
Low = Native
High = Native + 200 ms
```

Do not recalibrate delay from Stage 2.

## 4. Horizon selection

Do **not** hard-code `{10,15,25}` merely because those numbers were previously
discussed.

Use Stage 2 **ID-only** results to freeze three representative action-coverage
values before any new Stage 3 OOD outcomes are observed:

1. `H_low`: a lower-coverage value with clear RTC degradation at +200 ms;
2. `H_mid`: a transition / intermediate value;
3. `H_ref = 25`: the frozen Stage 1 reference operating point.

Constraints:

```text
H_low, H_mid ∈ {10,15,20}
H_ref = 25
H_low < H_mid < 25
```

Selection must use only Stage 2 ID results.

If Stage 2 shows no meaningful distinction among 10/15/20, default to:

```text
{10, 20, 25}
```

and record that the fallback was used.

Do not select 30 or 35 as the primary Stage 3 reference because the purpose is to
test robustness around/leading into the already-used 25-action Stage 1 point, not
to retrospectively replace it with a higher-performing configuration.

## 5. Primary method

```text
RTC
```

Naive async is not required for Stage 3 because Stage 1 already established severe
floor effects and the primary question concerns the RTC operating regime.

## 6. Factorial design

For each OOD candidate:

```text
scene ∈ {ID, OOD}
delay ∈ {Native, Native +200 ms}
n_action_steps ∈ {H_low, H_mid, 25}
seed ∈ [14..21]
method = RTC
```

Reuse matching ID controls across perturbations sharing the same base task.

## 7. Maximum run count

Four OOD candidates:

```text
4 × 3 horizons × 2 delays × 8 seeds = 192 OOD episodes
```

Shared ID controls for two unique base tasks:

```text
2 × 3 horizons × 2 delays × 8 seeds = 96 ID episodes
```

Total:

```text
288 new RTC episodes
```

If time is constrained, the post-hoc sensor-noise candidate is the first to cut:

```text
3 prespecified OOD candidates -> 144 OOD
+ 96 shared ID
= 240 episodes
```

## 8. Statistics

At each frozen horizon `h`:

```text
I_h =
  [S(OOD, high, h) - S(OOD, low, h)]
  -
  [S(ID, high, h) - S(ID, low, h)]
```

Report:
- raw successes / 8;
- Wilson intervals;
- paired seed differences;
- bootstrap CI for `I_h` when feasible;
- floor/ceiling diagnostics.

Primary confirmation asks whether the Stage 1 direction is reproduced at
`h=25`.

The additional lower horizons ask whether the localized interaction becomes
stronger as action coverage is reduced.

## 9. Required outputs

```text
stage3_horizon_selection.json
stage3_manifest.csv
stage3_episode_results.csv
stage3_four_cell_by_horizon.csv
stage3_interaction_by_horizon.csv
stage3_posthoc_sensor_noise.csv

stage3_interaction_vs_horizon.png
stage3_object_layout.png
stage3_robot_initial_state.png
stage3_lighting.png
stage3_sensor_noise_posthoc.png

STAGE_3_OOD_CONFIRMATION_OBSERVATIONS.md
```

## 10. Interpretation gate

Do not claim a general OOD × delay interaction unless the held-out data support it.

A defensible result may instead be:

> "The broad Stage 1 interaction was near null at the calibrated 25-action
> operating point, while selected task–perturbation cells showed reproducible,
> horizon-dependent degradation."

If localized effects do not replicate, report the broad null and the
non-replication.
