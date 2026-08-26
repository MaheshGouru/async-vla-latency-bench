# Experiment Matrix — After Completed Stage 1

## Seed allocation

```text
Stage 1 completed exploratory:  [0,1,2,3,4]
Stage 2 local sensitivity:      [5,6,7,8,9]
Stage 0 additional ID seeds:    [10,11,12,13]  (already completed)
Stage 3 held-out confirmation:  [14,15,16,17,18,19,20,21]
Stage 3B cross-task replication: [14,15,16,17,18,19,20,21]  (COMPLETE; same Stage 3 seed block)
Stage 3C initialization audit:  no rollout seeds; reset-only
```


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

## Post-Stage-3C active follow-up

Stage 3B completed with:

```text
spatial_transport: I={0,0,0} at h={20,25,30}
goal_drawer:       I={+0.125,+0.125,0}
long_stove_moka:   I={-0.125,-0.250,-0.125}
```

Thus the active follow-up is not a three-task family-wide layout sweep.

### Experiment A — required

Authoritative spec: `EXPERIMENT_A_OBJECT_LAYOUT_VARIANT_GENERALIZATION.md`.

```text
task = long_stove_moka
task type = multi_stage_sequential
suite/task_id = libero_10 / 2
perturbation = Objects Layout
new variants = exactly 3; deterministic freeze; exclude 1941/_add_25
method = RTC
n_action_steps = 25
delay = Native,+200 ms
seeds = [22,23,24,25,26,27,28,29]
initialization = libero_episode_index:0
new ID = 16
new OOD = 48
total = 64
```

### Experiment B — conditional

Authoritative spec: `EXPERIMENT_B_ADDITIONAL_MULTI_STAGE_TASK_GENERALIZATION.md`.

Dispatch gate:

```text
>=2/3 Experiment-A variants have I<0
AND mean I<0
AND validation/provenance clean
```

If dispatched:

```text
task = LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket
task type = multi_stage_sequential
suite/task_id = libero_10 / 0
perturbation = Objects Layout
variants = exactly 3, deterministically frozen
method = RTC
n_action_steps = 25
delay = Native,+200 ms
seeds = [30,31,32,33,34,35,36,37]
initialization = libero_episode_index:0
new ID = 16
new OOD = 48
total = 64
```

## Completed-result snapshot

```text
Stage 1: pooled I ≈ +1.4 pp -> no broad OOD amplification
Stage 2: at +200 ms, h20=h25=h30=14/15 pooled; h10=6/15
Stage 3: long_stove_moka × object_layout has I={-0.125,-0.250,-0.125}; other selected negative cells do not replicate
Stage 3B: cross-task object-layout result is task-dependent: spatial 0; goal non-negative; stove/moka negative
Stage 3C: failed closed; one distinct OOD initialization per frozen object-layout variant
```


## Stage 4 — second-policy diagnostic

```text
policy = OpenVLA-OFT combined four-suite checkpoint
tasks = 2
scenes = ID + exact Objects-Layout OOD
delays = Native,+200 ms
seeds = 38..45
execution = naive async
native action coverage = 8
```

Physical analysis episodes:

```text
2 tasks × 2 scenes × 2 delays × 8 seeds = 64
```

Smoke episodes:

```text
4 × seed999, excluded from analysis
```


## Stage 4 completed snapshot

```text
OpenVLA-OFT native/default coverage = 8
spatial_transport: I=+0.250; ID 8/8->6/8; OOD 8/8->8/8
long_stove_moka:   I=+0.125; ID 1/8->0/8; OOD 0/8->0/8
```

## Stage 5 — OpenVLA-OFT coverage calibration + conditional final replication

Stage 5A0 is a capability audit. If multiple legitimate coverages are exposed from one inference, Stage 5A uses:

```text
ID only
tasks = spatial_transport,long_stove_moka
delay = Native,+200 ms
coverage candidates = supported values frozen before outcomes; preferred {8,12,16,20,25} only if truly supported
seeds = 46..50
```

Stage 5B, if warranted:

```text
2 tasks × 2 scenes × 2 delays × 8 seeds = 64
seeds = 51..58
coverage = frozen Stage-5A operating point
exact OOD variants = same as Stage 4
```

## Stage 3 New — final high-power replication

Authoritative spec:

```text
STAGE_3_NEW_HIGH_POWER_REPLICATION.md
```

Frozen matrix:

```text
policy = π0.5
method = RTC
candidates = 6 unique Stage 3/3B task × perturbation pairs
horizons = 20,25,30
scene = ID/OOD
delay = Native,+200 ms
seeds = 46..173
n = 128 fresh seeds/cell
```

Physical run count with shared ID controls:

```text
OOD: 6 × 3 × 2 × 128 = 4,608
ID:  3 × 3 × 2 × 128 = 2,304
TOTAL = 6,912
```

Stage 5 OpenVLA calibration is canceled before execution.
