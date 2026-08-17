# Experiment B — Additional Multi-Stage Task Object-Layout Generalization

## 0. Status and frozen dispatch gate

**Status: CONDITIONAL.**

Run only if Experiment A satisfies its pre-frozen gate:

```text
>=2/3 new long_stove_moka variants have I<0
AND mean I across those 3 variants <0
AND no unresolved validation/provenance failure
```

Question:

> If the interaction repeats across multiple layouts of `long_stove_moka`, does it extend to a different multi-stage/sequential task?

## 1. Frozen new task

| field | frozen value |
|---|---|
| `task_key` | `additional_multistage_task` |
| task-demand type | `multi_stage_sequential` |
| suite | `libero_10` |
| base task id | `0` |
| exact base task name | `LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket` |

Before variant resolution, assert the installed standard-LIBERO task id 0 has this exact name. Fail closed on mismatch. Do not substitute a different task based on performance.

## 2. Frozen perturbation

```text
perturbation_key  = object_layout
official_category = Objects Layout
mechanism_group   = trajectory_adaptation
```

## 3. Freeze exactly three object-layout variants

Before any Experiment-B rollout outcome:

1. Load installed LIBERO-Plus `task_classification.json`.
2. Keep entries with the exact base-task prefix and `category == "Objects Layout"`.
3. Sort by `(abs(int(difficulty_level)-2), int(id))`.
4. Select the first **3** candidates.
5. Resolve each `api_task_index` by exact name lookup and assert equality.
6. Save exactly 3 rows to `experiment_b_frozen_object_layout_variants.csv`.
7. Record its SHA-256.
8. Rollout manifest must consume the frozen CSV directly.

Required columns:

```text
task_key
suite
base_task_id
base_task_name
task_demand_type
perturbation_key
official_category
mechanism_group
classification_id
api_task_index
difficulty_level
variant_name
```

## 4. Implementation/provenance requirements

Experiment B must use a distinct `experiment_b` provenance label and dedicated frozen-variant CSV, manifest, validator, and analysis outputs. It must not be dispatched merely because its code exists; dispatch is controlled exclusively by the frozen Experiment-A gate above.

Required provenance artifacts:

```text
experiment_b_frozen_object_layout_variants.csv
experiment_b_manifest.csv
experiment_b_episode_results.csv
experiment_b_invalid_episodes.csv
experiment_b_preflight_environment.json
experiment_b_smoke_validation.json
```

The runner must pass `episode_index=0` explicitly and fail closed if the resolved index is not zero.

Before analysis seeds, execute an isolated `seed=999` end-to-end smoke test. Smoke artifacts must remain outside the 64-row analysis manifest/results.

## 5. Exact execution configuration

```text
policy/checkpoint          = identical checkpoint + revision used in Stage 3/3B/Experiment A
method                     = RTC
configured_n_action_steps  = 25
control_rate_hz            = 20
control_period_ms          = 50
delay_conditions           = [Native, Native+200ms]
added_delay_ms             = [0, 200]
libero_episode_index       = 0
rollout_seeds              = [30,31,32,33,34,35,36,37]
```

Do not sweep horizons and do not reuse Experiment-A seeds.

## 6. Exact seed semantics

Use exactly `[30,31,32,33,34,35,36,37]` for every cell. These are rollout stochasticity replicates at initialization 0, not environment-initialization samples.

No substitution, adaptive expansion, or replacement of genuine task failures.

## 7. Initialization and pairing

Use exactly `libero_episode_index=0`.

For each fixed `(scene_condition, exact_variant_or_ID, rollout_seed)`, Native and +200 must have the same reset fingerprint and all non-delay configuration. ID and OOD fingerprints need not match because object layout intentionally changes geometry.

## 8. Exact episode matrix

Fresh ID:

```text
1 task × 2 delays × 8 seeds = 16 ID episodes
```

OOD:

```text
1 task × 3 variants × 2 delays × 8 seeds = 48 OOD episodes
```

Total:

```text
64 new physical episodes
```

The 16 ID rows are executed once and shared analytically across the three OOD comparisons.

## 9. Validation gates

Require exactly:

```text
manifest rows = 64
ID rows = 16
OOD rows = 48
new OOD variants = 3
seeds = {30,31,32,33,34,35,36,37}
delays = {0,200}
n_action_steps = {25}
method = {rtc}
requested/resolved initialization = 0
unique physical episode tuples = 64
```

Native/+200 pairs for a fixed `(scene_condition, exact_variant_or_ID, seed)` must share the same initialization fingerprint.

## 10. Analysis

For each variant:

```text
I_variant =
    [S(OOD,+200)-S(OOD,Native)]
  - [S(ID,+200)-S(ID,Native)]
```

Report raw successes/8 and paired-seed bootstrap intervals.

Interpretation is pre-frozen:

- repeated negative interactions support generalization beyond one task identity within a multi-stage regime;
- mixed/null results imply the vulnerability remains task-specific;
- no additional task may be substituted based on outcomes.
