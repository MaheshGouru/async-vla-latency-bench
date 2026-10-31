# Experiment A — Within-Task Object-Layout Variant Generalization

## 0. Status and scientific purpose

**Status: ACTIVE / REQUIRED NEXT EXPERIMENT.**

Stage 3B showed that the negative object-layout × delay interaction did **not** generalize across the two simpler task-demand categories:

```text
spatial_transport: I = 0 at h=20,25,30
goal_drawer:       I = +0.125,+0.125,0 at h=20,25,30
long_stove_moka:   I = -0.125,-0.250,-0.125 at h=20,25,30
```

Therefore the active question is:

> Does the negative object-layout × delay interaction on `long_stove_moka` persist across multiple independently selected object-layout variants of that same multi-stage task?

This is a **post-Stage-3B targeted generalization experiment**, not preregistered confirmation.

## 1. Frozen task

| field | frozen value |
|---|---|
| `task_key` | `long_stove_moka` |
| task-demand type | `multi_stage_sequential` |
| suite | `libero_10` |
| base task id | `2` |
| exact base task name | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it` |

Do not add `spatial_transport` or `goal_drawer`; Stage 3B already produced non-negative object-layout interactions for their frozen variants.

## 2. Frozen perturbation

```text
perturbation_key  = object_layout
official_category = Objects Layout
mechanism_group   = trajectory_adaptation
```

Previously evaluated variant, which must be excluded from new selection:

```text
classification_id = 1941
api_task_index     = 1940
difficulty_level   = 2
variant_name       = KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25
```

## 3. Freeze exactly three additional object-layout variants

Before any rollout outcome:

1. Load installed LIBERO-Plus `task_classification.json`.
2. Keep entries with exact base-name prefix and `category == "Objects Layout"`.
3. Exclude `classification_id=1941` / exact `_add_25` variant above.
4. Sort by `(abs(int(difficulty_level)-2), int(id))`.
5. Select the first **3** candidates.
6. Resolve each zero-based `api_task_index` by exact `variant_name` lookup.
7. Assert exact name equality.
8. Save exactly 3 rows to `experiment_a_frozen_object_layout_variants.csv`.
9. Record its SHA-256.
10. The rollout manifest consumes this frozen CSV directly; it must not rerun selection.

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

**Dispatch blocker:** no policy rollout until the three exact variant identities are frozen and verified.

## 4. Implementation/provenance requirements

Experiment A must be implemented as a distinct experiment label and must not masquerade as `stage3b`. Reuse the audited Stage-3 execution engine, but use dedicated Experiment-A manifest, runner/label, validator, and analysis entry points.

Required provenance artifacts:

```text
experiment_a_frozen_object_layout_variants.csv
experiment_a_manifest.csv
experiment_a_episode_results.csv
experiment_a_invalid_episodes.csv
experiment_a_preflight_environment.json
experiment_a_smoke_validation.json
```

Every result row must record at minimum:

```text
stage_or_experiment_label = experiment_a
analysis_status = targeted_post_stage3b_variant_generalization
manifest_sha256
spec_sha256
frozen_variant_csv_sha256
git_sha
lerobot_git_sha
libero_plus_git_sha
model_revision
checkpoint_id
runner_commit
environment_version
```

The runner must pass `episode_index=0` explicitly into the LIBERO/LIBERO-Plus environment constructor. Do not rely on the current function default. Record both requested and resolved initialization index, and fail closed if either is not zero.

Before using analysis seeds, run an isolated end-to-end smoke test with `seed=999` outside the 64-row analysis manifest. Smoke artifacts must not be included in the analysis CSV.

## 5. Exact execution configuration

```text
policy/checkpoint          = identical checkpoint + revision used in Stage 3/3B
method                     = RTC
configured_n_action_steps  = 25
control_rate_hz            = 20
control_period_ms          = 50
delay_conditions           = [Native, Native+200ms]
added_delay_ms             = [0, 200]
libero_episode_index       = 0
rollout_seeds              = [22,23,24,25,26,27,28,29]
```

Do not resweep `{20,25,30}`. This experiment isolates layout-variant generalization at the frozen central operating point.

## 6. Exact seed semantics

Use exactly `[22,23,24,25,26,27,28,29]` in every ID/OOD and Native/+200 cell. These are rollout stochasticity replicates at the benchmark-provided fixed initialization, not environment-initialization samples.

No seed substitution, adaptive extra seeds, or replacement of genuine task failures. Infrastructure-corrupted runs may rerun only with the identical tuple and seed.

## 7. Initialization and pairing

Use exactly `libero_episode_index:0`. Stage 3C showed that the relevant object-layout OOD interface exposes only one distinct initialization state; do not attempt indices 1–7.

For each fixed `(scene_condition, exact_variant_or_ID, rollout_seed)`, Native and +200 must share the same requested/resolved initialization and `initial_state_fingerprint`. Do not require ID and OOD fingerprints to match because object layout changes geometry.

## 8. Exact episode matrix

Fresh ID controls:

```text
1 task × 2 delays × 8 seeds = 16 ID episodes
```

New OOD:

```text
1 task × 3 new variants × 2 delays × 8 seeds = 48 OOD episodes
```

Total:

```text
64 new physical episodes
```

Run the 16 ID episodes once and share them analytically across the three OOD comparisons.

## 9. Unique episode identity

```text
(task_key,
 scene_condition,
 exact_variant_identity_or_ID,
 configured_n_action_steps=25,
 added_delay_ms,
 libero_episode_index=0,
 rollout_seed,
 method=RTC)
```

No duplicate physical tuple.

## 10. Validation gates

Before analysis, require all of the following:

```text
manifest rows = 64 exactly
ID rows = 16 exactly
OOD rows = 48 exactly
unique physical episode tuples = 64 exactly
new frozen OOD variants = 3 exactly
seeds = {22,23,24,25,26,27,28,29} exactly
delays = {0,200} exactly
n_action_steps = {25} exactly
method = {rtc} exactly
requested initialization = 0 for every row
resolved initialization = 0 for every row
status = ok for every scientifically valid completed row
```

For each `(scene_condition, exact_variant_or_ID, seed)`, Native and +200 must have identical initialization fingerprints. Corrupt/incomplete artifacts may be rerun only with the identical tuple. Genuine task failures remain task failures.

## 10. Primary analysis

For each new variant:

```text
I_variant =
    [S(OOD,+200)-S(OOD,Native)]
  - [S(ID,+200)-S(ID,Native)]
```

Report raw `successes/8` for all four cells and paired-seed bootstrap CIs, resampling the eight seed clusters and carrying all four cells together.

Keep the completed Stage-3 `_add_25` result separate:

```text
h=25: I=-0.250; OOD 3/8 -> 2/8
```

Do not pool old and new seed blocks as if they were one randomized experiment.

## 11. Frozen gate for Experiment B

Experiment B dispatches only if:

```text
at least 2 of 3 new variants have I_variant < 0
AND mean(I_variant across the 3 new variants) < 0
AND there is no unresolved validation/provenance failure
```

Do not relax this rule after seeing Experiment-A outcomes.


## Completion addendum — 2026-08-22

Experiment A completed with 64/64 valid analysis episodes.

```text
c1950 / level3_sample1: I = -0.375
c1953 / level4_sample2: I = +0.125
c1955 / level4_sample4: I = -0.125
mean I = -0.125
negative in 2/3 new variants
```

The frozen gate to Experiment B passed.
