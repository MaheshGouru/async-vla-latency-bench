# Experiment Matrix — After Completed Stage 1

## Seed allocation

```text
Stage 1 completed exploratory:  [0,1,2,3,4]
Stage 2 local sensitivity:      [5,6,7,8,9]
Stage 0 additional ID seeds:    [10,11,12,13]  (already completed)
Stage 3 held-out confirmation:  [14,15,16,17,18,19,20,21]
Stage 4 conditional VLASH:      [22,23,24,25,26]
```

Seed sets are fixed and disjoint across new stages.

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

## Stage 4 — conditional

```text
RTC vs VLASH
n_action_steps = 25
Native/+200 ms
up to 2 replicated OOD candidates
5 new seeds = 22..26
```

Maximum core: **80 analysis episodes**.


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

### Stage 4

If run, use new seeds `[22..26]` and reuse the exact Stage 3/Stage 1 variant IDs.
RTC and VLASH must be episode-matched.
