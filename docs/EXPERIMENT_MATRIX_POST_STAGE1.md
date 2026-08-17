# Experiment Matrix — After Completed Stage 1

## Seed allocation

```text
Stage 1 completed exploratory:  [0,1,2,3,4]
Stage 2 local sensitivity:      [5,6,7,8,9]
Stage 0 additional ID seeds:    [10,11,12,13]  (already completed)
Stage 3 held-out confirmation:  [14,15,16,17,18,19,20,21]
Stage 3B cross-task replication: [14,15,16,17,18,19,20,21]  (COMPLETE; same Stage 3 seed block)
Stage 3C initialization audit:  no rollout seeds; reset-only
Stage 3D rollout replicates:    [22,23]  (within-initialization replicates)
```

Seed allocation is frozen. Stage 3B intentionally reuses the Stage 3 seed block `[14..21]`; Stage 2 and Stage 4 remain disjoint.

## Stage 2 — required

```text
RTC
n_action_steps = 10,15,20,25,30,35
delay = Native,100,200,300 ms
3 ID tasks
5 seeds = 5..9

6 × 4 × 3 × 5 = 360 episodes
```

Purpose: defend the already-used 25/+200 operating point against local
configuration sensitivity.

## Stage 3 — required after Stage 2

```text
RTC
frozen horizons = 20,25,30
    20 = -5 around Stage 1
    25 = Stage 1 reference
    30 = +5 around Stage 1

delay = Native,+200 ms
8 held-out seeds = 14..21
```

Primary OOD candidates:
- object layout;
- robot initial state;
- lighting.

Post-hoc:
- sensor noise.

Maximum with post-hoc sensor noise: **288 episodes**.
Without sensor noise: **240 episodes**.

Required Stage 2 + primary Stage 3:

```text
360 + 240 = 600 episodes
```

Including the Stage 3 post-hoc sensor-noise replication:

```text
360 + 288 = 648 episodes
```


## Stage 3B — targeted object-layout cross-task replication

Stage 3B is selected after Stage 3 and is therefore labeled targeted/post-Stage-3,
not preregistered confirmation.

```text
RTC
tasks newly tested under object_layout = spatial_transport, goal_drawer
horizons = 20,25,30
delay = Native,+200 ms
seeds = 14..21
initialization_index_or_id = libero_episode_index:0
```

Exact new OOD variants:

| Task | `classification_id` | `api_task_index` | difficulty | Exact Stage 1 `variant_name` |
|---|---:|---:|---:|---|
| `spatial_transport` | `1773` | `1772` | `3` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15` |
| `goal_drawer` | `1891` | `1890` | `2` | `open_the_middle_drawer_of_the_cabinet_add_13` |

Accounting:

```text
new OOD: 2 × 3 × 2 × 8 = 96
new spatial ID: 1 × 3 × 2 × 8 = 48
reused Stage 3 goal ID: 48 existing rows
new execution total = 144 episodes
```

No new `long_stove_moka` episodes are run. The final three-task object-layout
analysis reuses its completed Stage 3 ID/OOD rows.

## Stage 3C — initialization diversity/determinism audit

Reset-only gate over all three object-layout task pairs:

```text
tasks = spatial_transport, goal_drawer, long_stove_moka
scenes = ID, exact frozen object-layout OOD
initialization_index = 0..7
repeat_resets = 3
policy_rollout_seeds = NONE
env_construction_seed = 0
policy_rollouts = 0
total_reset_operations = 144
```

Require 3/3 within-index fingerprint agreement and 8/8 distinct fingerprints
across indices within each task/scene. Freeze and hash
`stage3c_validated_initializations.csv` before Stage 3D.

## Stage 3D — initialization-generalization of surviving object-layout effects

Conditional task inclusion is computed exactly once from the completed Stage 3/3B outcomes using the documented post-Stage-3B directional rule. Freeze the result to `stage3d_surviving_tasks.json` with Stage 3/3B input hashes before manifest generation:

```text
include task iff I_25 < 0 and I_h < 0 at >=2 of {20,25,30}
```

Execution:

```text
RTC
n_action_steps = 25
delay = Native,+200 ms
initialization indices = 0,1,2,3,4,5,6,7
rollout seeds = 22,23
ID + exact frozen object-layout OOD
64 new episodes per surviving task
```

Stage 3D may consume only (1) the frozen `stage3d_surviving_tasks.json` and (2) the frozen Stage 3C validation artifact certifying eight valid, deterministic, distinct reset fingerprints per task/scene. The manifest must contain exactly 64 unique rows per admitted task and may not substitute tasks, initialization indices, seeds, horizons, or delays. The maximum is 192 new rollout episodes if all three object-layout tasks survive.

## Episode matching

### Stage 2

Use new seeds `[5..9]`. Do not reuse Stage 0/1 episodes.

For each `(task_key, seed)`, pair every horizon × delay cell on the same
initialization identity.

### Stage 3

Use new seeds `[14..21]`, but freeze the exact Stage 1 OOD variants:

| Follow-up status | Task | Perturbation | `classification_id` | `api_task_index` | Exact Stage 1 `variant_name` |
|---|---|---|---:|---:|---|
| Prespecified confirmatory | `long_stove_moka` | `object_layout` | `1941` | `1940` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25` |
| Prespecified confirmatory | `goal_drawer` | `robot_initial_state` | `285` | `284` | `open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_71` |
| Prespecified confirmatory | `goal_drawer` | `light_conditions` | `2313` | `2312` | `open_the_middle_drawer_of_the_cabinet_light_1` |
| Secondary post-hoc replication | `goal_drawer` | `sensor_noise` | `1509` | `1508` | `open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_0_noise_1` |

For every fixed task/variant/seed/scene, pair `{20,25,30}` ×
`{Native,+200}` on the same initialization identity wherever benchmark semantics
permit.


### Stage 3B

Use the same Stage 3 seeds `[14..21]`. For every newly executed
`(task, scene, exact variant, seed)`, all `{20,25,30} × {Native,+200}` cells must
use `libero_episode_index:0` and have one identical reset-state fingerprint.
Fingerprints need not differ across seeds.

For `goal_drawer`, reuse the exact 48 Stage 3 ID rows; do not rerun them. For
`spatial_transport`, run 48 new ID controls because Stage 3 has no spatial ID
rows. ID and object-layout OOD fingerprints are not required to match because
layout geometry is the treatment; match every non-perturbed factor.


### Stage 3C

Reset-only: use initialization indices `[0..7]` for all three task pairs, with three clean reset/fingerprint repetitions per task × scene × index. Require exact requested/resolved index equality, 3/3 repeat determinism, and 8/8 distinct fingerprints. No rollout seeds or policy outcomes.

### Stage 3D

Use only Stage 3C-validated initialization indices `[0..7]` and rollout seeds `[22,23]`. Native and +200 for a fixed task/scene/index/seed must share the same reset fingerprint. ID/OOD are paired by initialization index, not by equal geometry. Bootstrap by initialization cluster.
