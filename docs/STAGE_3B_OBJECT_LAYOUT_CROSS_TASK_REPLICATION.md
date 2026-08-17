# Stage 3B — Targeted Cross-Task Object-Layout Replication

## 0. Status and purpose

## Completion note

**Stage 3B is COMPLETE.** This file is retained as the frozen conduct/specification
record. Do not modify its experiment matrix or rerun it merely because Stage 3C
were added later.


remaining compute.

Stage 3B is a **post-Stage-3 targeted cross-task replication** prompted by the
held-out Stage 3 result: `long_stove_moka × object_layout` showed a negative
OOD × delay interaction with the same direction at all three frozen horizons,
while the other prespecified Stage 3 perturbations did not reproduce a negative
interaction.

Stage 3B asks one narrow question:

> Does the object-layout × delay interaction generalize from the multi-stage
> `long_stove_moka` task to the two other task-demand categories that were already
> part of the Stage 1 benchmark?

This experiment must **not** be described as preregistered or as part of the
original Stage 3 confirmation. It is a targeted follow-up selected after viewing
Stage 3 outcomes.

Stage 0 and Stage 1 files remain unchanged.


## 0A. Historical handoff rule for post-Stage-3B follow-up


```text
    I_25 < 0
    AND I_h < 0 at at least 2 of {20,25,30}
```


## 1. Tasks

Add object-layout OOD only for the two Stage 1 tasks that did not receive an
object-layout follow-up in Stage 3:

```text
spatial_transport   # single-stage transport
    suite = libero_spatial
    base_task_id = 2
    base_task_name = pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate

goal_drawer         # articulated/contact-rich
    suite = libero_goal
    base_task_id = 0
    base_task_name = open_the_middle_drawer_of_the_cabinet
```

Do **not** add new arbitrary LIBERO tasks in Stage 3B.

The third task-demand category is already supplied by the completed Stage 3
object-layout result:

```text
long_stove_moka     # multi-stage/sequential
```

No new `long_stove_moka` episodes are required.

## 2. Exact frozen object-layout variants

Use the exact object-layout variants resolved **before Stage 1 outcomes** in
`stage1_resolved_variants.csv`.

| Task | Task-demand group | `classification_id` | `api_task_index` | `difficulty_level` | Exact `variant_name` |
|---|---|---:|---:|---:|---|
| `spatial_transport` | single-stage transport | `1773` | `1772` | `3` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15` |
| `goal_drawer` | articulated/contact-rich | `1891` | `1890` | `2` | `open_the_middle_drawer_of_the_cabinet_add_13` |
| `long_stove_moka` | multi-stage/sequential; completed Stage 3 reference | `1941` | `1940` | `2` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25` |

The first two rows are the only new OOD variants dispatched in Stage 3B. The
third row is included only to define the final three-task cross-task analysis.

Before dispatch, assert literal equality of all of:

```text
task_key
suite
base_task_id
perturbation_key == object_layout
classification_id
api_task_index
difficulty_level
variant_name
```

Also verify against the frozen `stage1_resolved_variants.csv` artifact. Do not
re-run the Stage 1 resolver and do not choose another object-layout variant.

## 3. Seeds

Use exactly the **same held-out seed block as Stage 3**:

```text
SEEDS = [14, 15, 16, 17, 18, 19, 20, 21]
```

Rationale:

- Stage 3B is testing cross-task generalization under the same held-out rollout
  seed block used for the original Stage 3 object-layout result;
- reusing these seeds permits exact reuse of the completed `goal_drawer` ID
  controls from Stage 3;
- the two new object-layout OOD task conditions were not evaluated in Stage 3.

Important interpretation:

> Stage 3B is a cross-task replication, **not an independent new-seed
> replication of Stage 3**.

Do not:

- replace seeds after failures;
- use different seed sets for `spatial_transport` and `goal_drawer`;
- use Stage 2 seeds `[5..9]` to avoid running the required Stage 3B ID controls.

Infrastructure-corrupted episodes may be rerun only with the same seed.

## 4. Execution configuration

Keep the completed Stage 3 execution regime unchanged:

```text
method = RTC
n_action_steps = {20,25,30}
delay = {Native, Native +200 ms}
control_rate = 20 Hz
control_period_ms = 50
checkpoint = same exact π0.5 checkpoint/revision used in Stage 3
RTC delay estimator = same request-specific causal implementation used in Stage 3
```

Stage 2 must not be used to select or change any Stage 3B horizon.

The Stage 3B manifest must contain exactly:

```text
new OOD:
    spatial_transport × object_layout
    goal_drawer × object_layout

new ID:
    spatial_transport only

reused completed Stage 3 ID:
    goal_drawer only

reused completed Stage 3 object-layout pair for final cross-task analysis:
    long_stove_moka ID + object_layout
```

## 5. Initialization identity — exact protocol

### 5.1 Initialization index

Use the same benchmark initialization protocol as Stages 2–3:

```text
initialization_index_or_id = libero_episode_index:0
```

for every newly executed Stage 3B episode.

Do not cycle initialization indices by seed, horizon, or delay.

The prior stages show that the benchmark reset fingerprint can remain identical
across different policy seeds. Therefore **do not require distinct reset
fingerprints across seeds**. The seed is a rollout/policy seed; it is not evidence
that the simulator reset state changed.

### 5.2 Six-cell pairing within each scene

For each fixed:

```text
(task_key, scene_condition, exact_variant_identity, seed)
```

all six cells:

```text
n_action_steps ∈ {20,25,30}
added_delay_ms ∈ {0,200}
```

must begin from exactly the same reset state.

Assert:

```text
one initialization_index_or_id per task/scene/variant/seed
one initial_state_fingerprint per task/scene/variant/seed
six unique horizon×delay cells
```

Any failure of this audit is a **dispatch blocker**.

### 5.3 ID ↔ OOD pairing for object layout

Object layout intentionally changes scene geometry. Therefore do **not** require
ID and OOD reset-state fingerprints to be equal.

Instead, ID and OOD must match on every non-treatment factor:

```text
base task
seed
libero_episode_index:0
checkpoint/revision
RTC implementation
action representation
control period
horizon
delay condition
preprocessing
hardware/runtime class where feasible
```

The OOD geometry must remain exactly that encoded by the frozen Stage 1
object-layout variant.

### 5.4 Reuse of completed Stage 3 goal ID controls

For `goal_drawer`, do **not** rerun ID controls.

Reuse the exact 48 completed Stage 3 ID rows:

```text
1 task
× 3 horizons
× 2 delays
× 8 seeds
= 48 existing ID episodes
```

The reused rows must retain their original:

```text
run_id
seed
initialization_index_or_id
initial_state_fingerprint
manifest/spec provenance
request/action artifact references
```

Do not copy them into new run IDs and do not count them twice in any aggregate.

Before reuse, assert that all 48 expected Stage 3 goal-ID cells exist, are valid,
and match the Stage 3B checkpoint/timing semantics.

### 5.5 New spatial ID controls

Stage 3 did not contain `spatial_transport` ID controls. Therefore Stage 3B must
run them rather than borrowing Stage 2 or Stage 1 controls.

Run exactly:

```text
spatial_transport
scene = ID
seed = 14..21
n_action_steps = 20,25,30
delay = Native,+200 ms
initialization_index_or_id = libero_episode_index:0
```

This is:

```text
3 × 2 × 8 = 48 new spatial ID episodes
```

These are the only new ID episodes in Stage 3B.

## 6. New run count

### New OOD episodes

```text
2 tasks
× 3 horizons
× 2 delays
× 8 seeds
= 96 new OOD episodes
```

### New ID episodes

Only `spatial_transport` needs new matching ID controls:

```text
1 task
× 3 horizons
× 2 delays
× 8 seeds
= 48 new ID episodes
```

### Total new Stage 3B execution

```text
96 OOD + 48 ID = 144 new episodes
```

Do not report Stage 3B as 96 new episodes. That would omit the required
same-seed spatial ID controls.

## 7. Analysis accounting

For each task and horizon compute the same four-cell interaction used in Stage 3:

```text
I_h(task) =
    [S(OOD,+200,h) - S(OOD,Native,h)]
    -
    [S(ID,+200,h) - S(ID,Native,h)]
```

Each success cell has exactly 8 rollout trials.

### Stage 3B two-task analysis table

The logical two-task analysis contains:

```text
2 tasks × 2 scenes × 3 horizons × 2 delays × 8 seeds
= 192 analysis rows
```

Composition:

```text
144 newly executed Stage 3B rows
48 reused Stage 3 goal-ID rows
```

Deduplicate by original `run_id` before any pooled accounting.

### Three-task object-layout synthesis

For the final cross-task figure/table, combine:

```text
spatial_transport   Stage 3B ID + Stage 3B object-layout OOD
goal_drawer         Stage 3 reused ID + Stage 3B object-layout OOD
long_stove_moka     Stage 3 ID + Stage 3 object-layout OOD
```

This yields a logical:

```text
3 tasks × 2 scenes × 3 horizons × 2 delays × 8 seeds
= 288 unique analysis rows
```

No episode may appear more than once in this 288-row table.

## 8. Statistics

Primary Stage 3B quantities are **task-specific**, not a single pooled family
claim.

For each of `spatial_transport` and `goal_drawer`, report at each horizon:

```text
ID Native successes / 8
ID +200 successes / 8
OOD Native successes / 8
OOD +200 successes / 8
I_h
paired-seed bootstrap CI for I_h
Wilson interval for each success rate
```

Use the same seed-clustered pairing implementation as Stage 3. Resample the eight
seed clusters; never bootstrap individual episode rows independently.

Then show the already completed `long_stove_moka` object-layout result alongside
the two Stage 3B tasks.

Do not elevate a pooled three-task average over the task-specific results. The
scientific question is whether direction/effect generalizes across task demands.

## 9. Interpretation gate

The wording is determined by the cross-task pattern.

If all three task-demand categories show a negative interaction in the same
region, a defensible statement is:

> Object-layout shifts show a reproducible tendency to reduce delay tolerance
> across diverse manipulation demands in this benchmark.

If only a subset is negative:

> Object-layout × delay interactions are task-dependent rather than a universal
> family effect.

If only `long_stove_moka` remains negative:

> The replicated interaction is localized to the tested multi-stage task; the
> data do not support a general object-layout family claim.

Do not call Stage 3B confirmatory evidence for a family-wide hypothesis without
explicitly noting that this follow-up was selected after seeing the Stage 3
object-layout result.

## 10. Required manifest gates

Before dispatch, assert all of the following:

```text
new_rows == 144
new_ood_rows == 96
new_id_rows == 48

new tasks == {spatial_transport, goal_drawer}
new OOD perturbation == object_layout
method == rtc
horizons == {20,25,30}
delays_ms == {0,200}
seeds == {14,15,16,17,18,19,20,21}
initialization_index_or_id == libero_episode_index:0

spatial OOD exact identity == (1773,1772,difficulty=3,..._add_15)
goal OOD exact identity == (1891,1890,difficulty=2,..._add_13)

for every newly-run task/scene/variant/seed:
    exactly 6 horizon×delay cells
    exactly 1 initialization ID
    exactly 1 reset-state fingerprint

goal ID new rows == 0
long_stove_moka new rows == 0
```

The analysis builder must separately assert:

```text
stage3b_two_task_analysis_rows == 192 unique run_id rows
object_layout_three_task_analysis_rows == 288 unique run_id rows
```

## 11. Required outputs

```text
stage3b_object_layout_manifest.csv
stage3b_episode_results.csv
stage3b_initialization_pairing_audit.csv
stage3b_reused_stage3_controls_audit.csv
stage3b_four_cell_by_task_horizon.csv
stage3b_interaction_by_task_horizon.csv
stage3b_object_layout_three_task_analysis.csv
stage3b_object_layout_cross_task.png
STAGE_3B_OBJECT_LAYOUT_OBSERVATIONS.md
```

Record a Stage 3B specification hash and manifest hash per new result row.
Preserve the original Stage 3 provenance fields on reused rows.

## 12. Stop rule

Do not add additional tasks, object-layout variants, perturbation families, or
seeds after inspecting Stage 3B outcomes as part of this stage.

Stage 3B ends after the frozen 144 new episodes and the predefined three-task
analysis above. Any further expansion must be labeled as a separate exploratory
stage.


---

## Completed Stage 3B results

Stage 3B completed successfully under the frozen conduct above.

Archive provenance:

```text
stage3b_results.tar.gz
SHA-256 d4ab1b7ad75fec70ca7a6d48a6e3f11458bab84f0ee5c59daa96c19bb50a50c2
```

Three-task object-layout interaction results:

| task | task-demand type | h=20 | h=25 | h=30 |
|---|---|---:|---:|---:|
| `spatial_transport` | single-stage transport | 0.000 | 0.000 | 0.000 |
| `goal_drawer` | articulated/contact-rich | +0.125 | +0.125 | 0.000 |
| `long_stove_moka` | multi-stage/sequential | -0.125 | -0.250 | -0.125 |

Raw four-cell results:

| task | h | ID Native | ID +200 | OOD Native | OOD +200 |
|---|---:|---:|---:|---:|---:|
| `spatial_transport` | 20 | 8/8 | 8/8 | 8/8 | 8/8 |
| `spatial_transport` | 25 | 8/8 | 8/8 | 8/8 | 8/8 |
| `spatial_transport` | 30 | 8/8 | 8/8 | 8/8 | 8/8 |
| `goal_drawer` | 20 | 6/8 | 5/8 | 8/8 | 8/8 |
| `goal_drawer` | 25 | 7/8 | 6/8 | 8/8 | 8/8 |
| `goal_drawer` | 30 | 7/8 | 7/8 | 8/8 | 8/8 |
| `long_stove_moka` | 20 | 8/8 | 8/8 | 3/8 | 2/8 |
| `long_stove_moka` | 25 | 7/8 | 8/8 | 3/8 | 2/8 |
| `long_stove_moka` | 30 | 8/8 | 8/8 | 4/8 | 3/8 |

Paired-seed bootstrap 95% CIs for the interaction:

```text
spatial_transport: h20 [0,0], h25 [0,0], h30 [0,0]
goal_drawer:       h20 [0,+0.375], h25 [0,+0.375], h30 [0,0]
long_stove_moka:   h20 [-0.500,+0.250], h25 [-0.625,0], h30 [-0.375,0]
```

**Frozen interpretation:** object layout is not a task-general perturbation-family effect in this study. The negative interaction is localized to the multi-stage `long_stove_moka` task among the three evaluated task-demand categories. The next experiment therefore tests multiple object-layout variants of that same task before adding another multi-stage task.
