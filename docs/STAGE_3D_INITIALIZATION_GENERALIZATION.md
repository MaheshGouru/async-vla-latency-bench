# Stage 3D — Initialization-Generalization of Surviving Object-Layout Effects

## 0. Status and purpose

Run **after completed Stage 3B and after Stage 3C initialization audit passes**. Stage 3D addresses the main remaining external-validity
limitation of Stages 3/3B: those experiments use `libero_episode_index:0`, so
rollout seeds measure policy/rollout stochasticity at one benchmark reset rather
than robustness across distinct environment initializations.

Stage 3D asks:

> Does an object-layout × delay interaction that survives the cross-task Stage 3B
> test persist across distinct benchmark initializations of that task?

This is a conditional, post-Stage-3B follow-up. Task inclusion is determined from
the completed Stage 3/3B object-layout results using the directional rule below.
Because Stage 3B is already complete, this selection must **not** be described as
preregistered or independent confirmation. Once the Stage 3D task list is generated
and frozen, do not expand or narrow it after looking at Stage 3D outcomes.

Stage 0 and Stage 1 files remain unchanged.

## 0A. Required Stage 3C handoff

Stage 3D may dispatch only from the frozen Stage 3C artifact:

```text
stage3c_validated_initializations.csv
```

For every task/scene that enters Stage 3D, this artifact must certify exactly the
initialization indices `{0,1,2,3,4,5,6,7}` as deterministic and distinct within
that task/scene. Stage 3D may not substitute a different index after observing
rollout outcomes.

Stage 3C is reset-only and contains no policy rollouts; Stage 3D is the first stage
that uses the validated initialization axis for outcome analysis.

## 1. Which tasks enter Stage 3D

Evaluate the three object-layout task pairs available after Stage 3B:

```text
spatial_transport × object_layout
goal_drawer × object_layout
long_stove_moka × object_layout
```

For each task and horizon `h ∈ {20,25,30}`, compute the same Stage 3/3B
interaction:

```text
I_h = [S_OOD(+200) - S_OOD(Native)]
      - [S_ID(+200) - S_ID(Native)]
```

A task is a **surviving object-layout effect** and enters Stage 3D iff:

```text
I_25 < 0
AND
I_h < 0 at at least 2 of the 3 frozen horizons {20,25,30}
```

This is a directional persistence rule, not a significance threshold. Use it
mechanically and save the resulting task list plus the hashes of the Stage 3/3B
inputs before any Stage 3D rollout. Do not use bootstrap CI inclusion/exclusion,
effect magnitude, or visual inspection to make exceptions.

The completed Stage 3 `long_stove_moka × object_layout` result already satisfies
this rule. `spatial_transport` and `goal_drawer` are admitted only if their Stage
3B outcomes satisfy the same rule.

Possible Stage 3D task counts are therefore:

```text
1 task:  long_stove_moka only
2 tasks: long_stove_moka + one Stage 3B survivor
3 tasks: all three object-layout tasks
```

Do not add a task that fails the rule and do not add unrelated LIBERO tasks.

### 1.1 Freeze the Stage 3D task list before dispatch

Because Stage 3B is already complete, evaluate the rule exactly once from the
frozen Stage 3 + Stage 3B result artifacts and write:

```text
stage3d_surviving_tasks.json
```

The file must contain, for each of the three candidate tasks, the three values
`I_20`, `I_25`, `I_30`, the boolean result of the mechanical survival rule, and
for each admitted task its exact ID task identity and exact object-layout OOD
identity. Also record:

```text
survival_rule_version = stage3d_v1
stage3_input_sha256
stage3b_input_sha256
stage3d_surviving_tasks_sha256
```

The Stage 3D manifest generator must consume this frozen file. It must **not**
recompute task inclusion from mutable analysis outputs at dispatch time. If the
file is missing, unhashed, or disagrees with the literal rule above, Stage 3D is
blocked.

## 2. Execution configuration

Stage 3D tests initialization generalization at the frozen central operating point;
it is not another horizon sweep.

Use exactly:

```text
method = RTC
n_action_steps = 25
delay = {Native, Native +200 ms}
control_rate = 20 Hz
control_period_ms = 50
checkpoint = exact same π0.5 checkpoint/revision as Stage 3/3B
RTC delay estimator = exact same request-specific causal implementation
```

Do not reselect the horizon or delay after Stage 3B.

## 3. Initialization set — frozen and validated by Stage 3C

Use exactly the initialization indices validated in Stage 3C. The purpose is to
turn initialization identity into the generalization axis. The set is literal and
immutable:

```text
INITIALIZATION_INDICES = [0,1,2,3,4,5,6,7]
```

No modulo, wraparound, fallback, replacement, adaptive selection, or substitution
is permitted. An invalid or non-distinct index blocks Stage 3D rather than changing
the set.

### 3.1 Mandatory Stage 3C validation artifact

Stage 3C must already have completed the reset-only audit for every
surviving task and for both its ID scene and exact frozen object-layout OOD scene.
No policy inference or task success outcome may be collected during this audit.

For each `(task, scene, initialization_index)`:

1. construct/reset the environment exactly three times using that exact index and
   the fixed Stage 3C environment-construction seed `0`;
2. record the complete canonical reset-state fingerprint on all three resets;
3. require all three fingerprints to be identical;
4. require indices `0..7` to produce eight distinct fingerprints within that
   task/scene.

Required preflight invariants:

```text
8 valid initialization indices per task/scene
8 unique reset-state fingerprints per task/scene
repeat-reset fingerprint equality for each index
```

If any candidate index is invalid, aliases another index, or is nondeterministic:

> **STOP Stage 3D. Do not silently replace the index.**

Stage 3D must consume the exact Stage 3C validated initialization manifest; it must not rediscover, replace, or reorder initialization indices.

Resolve how the pinned benchmark exposes distinct initialization states, revise
and re-freeze this document/manifest **before any policy rollout**, then rerun the
reset-only audit. Never choose replacement initializations based on success
outcomes.

### 3.2 ID ↔ OOD initialization pairing

For each surviving task, pair ID and object-layout OOD by the **same benchmark
initialization index**:

```text
ID index j  ↔  OOD index j, for j = 0..7
```

Do **not** require the ID and OOD fingerprints to be equal. Object layout is the
treatment and intentionally changes scene geometry. Pairing requires the same
index and every non-treatment factor, not geometric identity.

## 4. Rollout seeds

Use exactly two new rollout/policy seeds at every initialization:

```text
ROLLOUT_SEEDS = [22,23]
```

These seeds are used as **within-initialization rollout replicates**. They are not
the initialization-generalization units. The seed block is literal and immutable:
there is no seed-per-initialization assignment, no replacement seed, and no adaptive
seed selection.

For every surviving task, use both seeds for every:

```text
scene ∈ {ID, object_layout_OOD}
initialization_index ∈ {0..7}
delay ∈ {Native,+200 ms}
```

Do not:

- use seeds `14..21` as substitutes for the Stage 3D rollout seeds;
- assign different rollout seeds to ID and OOD;
- assign different rollout seeds by initialization or delay;
- replace a genuine task failure with another seed.

Infrastructure-corrupted episodes may be rerun only with the same
`(task, scene, initialization_index, rollout_seed, delay)` identity.

## 5. Per-cell reset matching

For each fixed:

```text
(task, scene, exact_variant_identity, initialization_index, rollout_seed)
```

the two delay cells:

```text
Native
Native +200 ms
```

must start from exactly the same reset state.

Assert:

```text
one initialization_index_or_id
one initial_state_fingerprint
two unique delay cells
```

The fingerprint must match across the two delays. It may differ across
initialization indices and must differ across indices according to the reset-only
preflight.

### 5.1 Exact Stage 3D episode identity

Every Stage 3D rollout is uniquely identified by the full tuple:

```text
(task_key,
 scene_condition,
 exact_variant_identity,
 initialization_index,
 rollout_seed,
 execution_method=RTC,
 n_action_steps=25,
 added_delay_ms)
```

where `added_delay_ms ∈ {0,200}`. The manifest must contain exactly one row for
every intended tuple and zero duplicate tuples. Resume/retry logic must preserve
this complete identity. A genuine task failure is final for that tuple; only an
infrastructure-corrupted rollout may be rerun, and only with the identical tuple.

## 6. Exact OOD variants

Use the same exact frozen Stage 1 object-layout identity for each surviving task:

| Task | `classification_id` | `api_task_index` | difficulty | Exact `variant_name` |
|---|---:|---:|---:|---|
| `spatial_transport` | `1773` | `1772` | `3` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15` |
| `goal_drawer` | `1891` | `1890` | `2` | `open_the_middle_drawer_of_the_cabinet_add_13` |
| `long_stove_moka` | `1941` | `1940` | `2` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25` |

Only rows for tasks that satisfy the frozen survival rule are dispatched. Do not
resolve or substitute another object-layout variant.

## 7. Episode accounting

For each surviving task:

```text
8 distinct initialization indices
× 2 rollout seeds
× 2 scenes [ID, OOD]
× 2 delays [Native,+200]
× 1 horizon [25]
= 64 new episodes per task
```

Therefore:

```text
1 surviving task  ->  64 new episodes
2 surviving tasks -> 128 new episodes
3 surviving tasks -> 192 new episodes
```

Run a balanced Stage 3D block even for `initialization_index=0`; do not reuse old
Stage 3/3B rows because those use a different rollout-seed block and would make
the initialization comparison unbalanced.

## 8. Manifest requirements

The Stage 3D manifest must include at minimum:

```text
analysis_status = initialization_generalization
source_stage = stage3c
survival_rule_version
survival_rule_inputs_hash
stage3d_surviving_tasks_sha256
task_key
suite
base_task_id
scene_condition
perturbation_key
classification_id
api_task_index
variant_name
difficulty_level
requested_initialization_index
resolved_initialization_index_or_id
initial_state_fingerprint
rollout_seed
execution_method
n_action_steps
added_delay_ms
checkpoint_id
checkpoint_revision
runner_commit
environment_version
stage3d_spec_hash
manifest_hash
```

Before dispatch, assert all of the following:

```text
exact literal OOD variant identity for every admitted task
INITIALIZATION_INDICES == [0,1,2,3,4,5,6,7]
ROLLOUT_SEEDS == [22,23]
execution_method == RTC for every row
n_action_steps == 25 for every row
added_delay_ms set == {0,200}
exactly 64 rows per admitted task
exactly 64 × number_of_surviving_tasks total rows
zero duplicate full episode-identity tuples
zero rows for tasks absent from stage3d_surviving_tasks.json
```

## 9. Primary analysis

The **generalization unit is initialization**, not rollout seed.

For each task and initialization index `j`, first average success over the two
rollout seeds within each of the four cells:

```text
ID Native
ID +200
OOD Native
OOD +200
```

Then compute:

```text
I_j = [S_OOD,j(+200) - S_OOD,j(Native)]
      - [S_ID,j(+200) - S_ID,j(Native)]
```

Report per task:

```text
mean I across 8 initialization indices
median I across 8 initialization indices
number of initialization indices with I_j < 0
raw successes/trials for all four cells
per-initialization I_j values
```

For uncertainty, use an **initialization-clustered bootstrap**:

- resample the 8 initialization indices with replacement;
- when an index is sampled, carry the complete cluster for that index: both rollout
  seeds × both scenes × both delays (8 episode rows per task/index);
- do not bootstrap individual episodes or rollout seeds independently;
- do not treat the 16 rollout episodes per scene/delay as 16 independent
  initialization draws.

## 10. Interpretation rules

Stage 3D can support progressively stronger statements:

- effect persists across most initializations: evidence for within-task
  initialization-generalization of the object-layout × delay interaction;
- effect is concentrated in a few initializations: interaction is state-dependent;
- average interaction disappears across initializations: the Stage 3/3B fixed-init
  result does not generalize over reset states.

Do not claim population-wide LIBERO robustness from eight initializations. Do not
collapse all tasks and initializations into one headline number without first
showing task-specific and initialization-specific results.

## 11. Dispatch gates

Stage 3D may start only after all are true:

```text
[ ] Stage 3B complete and frozen
[ ] survival rule evaluated mechanically and saved
[ ] `stage3d_surviving_tasks.json` frozen and SHA-256 recorded
[ ] Stage 3D manifest consumes that frozen survivor file without recomputing selection
[ ] surviving-task list saved before Stage 3D rollouts
[ ] exact OOD identities validated
[ ] reset-only audit passes for indices 0..7 in ID and OOD
[ ] eight distinct fingerprints per task/scene verified
[ ] Stage 3C used exactly 3 resets per task/scene/index with constructor seed 0
[ ] repeated reset determinism verified
[ ] initialization indices exactly [0,1,2,3,4,5,6,7], with no substitution
[ ] rollout seeds exactly [22,23], with no substitution
[ ] n_action_steps exactly 25
[ ] delays exactly Native/+200 ms
[ ] same checkpoint/RTC/timing semantics as Stage 3/3B
[ ] manifest has exactly 64 rows per admitted task and 64 × number of surviving tasks total
[ ] manifest full episode-identity tuple is unique for every row
[ ] initialization-clustered analysis test passes on toy data
```
