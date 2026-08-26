# Stage 3 New — High-Power Replication of the Stage 3 / Stage 3B Matrix

## 0. Status

**ACTIVE NEXT EXPERIMENT**

Canonical filename:

```text
STAGE_3_NEW_HIGH_POWER_REPLICATION.md
```

This is the final planned π0.5 experiment before paper freeze.

It is a **fresh, high-replication rerun** of the union of the completed Stage 3
and Stage 3B task × perturbation × horizon conditions.

It is **not**:

- a new exploratory screen;
- a new task-selection experiment;
- a new perturbation-selection experiment;
- an OpenVLA experiment;
- a search for a stronger positive result;
- a pooling of the old eight rollout seeds with new seeds.

The sole substantive change is **statistical replication**.

The final replication target is **64 completely fresh seeds per unique cell**, chosen as the compute-feasible compromise between the original `n=8` design and the initially considered `n=128` design.

---

## 1. Motivation

The completed Stage 3 / Stage 3B interaction estimates used only eight rollout
seeds per cell. With binary success outcomes, an interaction

```text
I =
  [S(OOD,+200) - S(OOD,Native)]
  -
  [S(ID,+200) - S(ID,Native)]
```

can therefore change in increments of `1/8 = 0.125`.

A conservative independent-binomial worst-case approximation gives:

```text
SE(I) <= sqrt(4 * 0.25 / n) = 1/sqrt(n)
```

so:

```text
n = 8   -> SE(I) <= 0.354 -> ~95% half-width <= 0.69
n = 64  -> SE(I) <= 0.125 -> ~95% half-width <= 0.25
```

The previous qualitative conclusion that OOD × delay interactions were sparse
and heterogeneous may therefore be sensitive to small-sample rollout noise.

Stage 3 New directly addresses that weakness by rerunning the **same scientific
conditions** with:

```text
64 completely fresh rollout seeds per unique cell
```

The old Stage 3 / 3B rows remain historical discovery/low-replication evidence
and are not included in the primary Stage 3 New estimates.

---

## 2. What changes relative to Stage 3 / Stage 3B

### Unchanged

```text
policy family             = pi0.5
checkpoint                 = same exact checkpoint/revision used in Stages 1–3B
execution method           = RTC
control rate               = 20 Hz
control period             = 50 ms
added delay                = {0, 200} ms
delay labels               = {Native, Native +200 ms}
configured action coverage = {20, 25, 30}
LIBERO episode index       = 0
OOD variants               = exact frozen Stage-1 variants used in Stage 3 / 3B
interaction definition     = same difference-in-differences I
```

### Changed

```text
old Stage 3 / 3B seeds     = 14..21  (8 seeds)
Stage 3 New seeds          = 46..109 (128 completely fresh seeds)
```

No old Stage 3 / Stage 3B success rows are pooled into the primary Stage 3 New
analysis.

---

## 3. Exact fresh seed block

Use exactly:

```python
SEEDS = list(range(46, 110))
assert len(SEEDS) == 64
assert SEEDS[0] == 46
assert SEEDS[-1] == 109
```

Do not replace failed policy rollouts with different seeds.

Infrastructure-invalid episodes may be rerun only with the **same** seed and
same frozen condition.

---

## 4. Exact candidate matrix

Stage 3 New reruns the **union of unique Stage 3 and Stage 3B conditions**.

### 4.1 Stage-3 candidates

These four conditions must all be rerun. The sensor-noise row remains explicitly
labeled post-hoc; increasing replication does not make its original selection
prespecified.

| `candidate_key` | Original status | Task | Perturbation | `classification_id` | `api_task_index` | difficulty | Exact frozen `variant_name` |
|---|---|---|---|---:|---:|---:|---|
| `long_stove_object_layout` | Stage-3 prespecified | `long_stove_moka` | `object_layout` | `1941` | `1940` | `2` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25` |
| `goal_robot_initial_state` | Stage-3 prespecified | `goal_drawer` | `robot_initial_state` | `285` | `284` | `2` | `open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_71` |
| `goal_light_conditions` | Stage-3 prespecified | `goal_drawer` | `light_conditions` | `2313` | `2312` | `2` | `open_the_middle_drawer_of_the_cabinet_light_1` |
| `goal_sensor_noise_posthoc` | Stage-3 secondary post-hoc | `goal_drawer` | `sensor_noise` | `1509` | `1508` | `2` | `open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_0_noise_1` |

### 4.2 Stage-3B cross-task object-layout additions

These two rows complete the three-task object-layout comparison. The
`long_stove_moka × object_layout` row above is the overlap between Stage 3 and
Stage 3B and must be executed **once**, not duplicated.

| `candidate_key` | Original status | Task | Perturbation | `classification_id` | `api_task_index` | difficulty | Exact frozen `variant_name` |
|---|---|---|---|---:|---:|---:|---|
| `spatial_object_layout` | Stage-3B targeted follow-up | `spatial_transport` | `object_layout` | `1773` | `1772` | `3` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15` |
| `goal_object_layout` | Stage-3B targeted follow-up | `goal_drawer` | `object_layout` | `1891` | `1890` | `2` | `open_the_middle_drawer_of_the_cabinet_add_13` |

Therefore Stage 3 New contains exactly:

```text
6 unique task × perturbation candidate pairs
3 unique base tasks
3 horizons
2 delay conditions
2 scene conditions for each candidate analysis
64 fresh rollout seeds
```

---

## 5. Exact base tasks

| `task_key` | suite | base task ID | Exact LIBERO task |
|---|---|---:|---|
| `spatial_transport` | `libero_spatial` | `2` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate` |
| `goal_drawer` | `libero_goal` | `0` | `open_the_middle_drawer_of_the_cabinet` |
| `long_stove_moka` | `libero_10` | `2` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it` |

Do not substitute a different task or variant after dispatch.

---

## 6. Exact factorial design

For each unique OOD candidate:

```text
scene ∈ {ID, OOD}
delay ∈ {Native, Native +200 ms}
n_action_steps ∈ {20,25,30}
seed ∈ {46,...,109}
method = RTC
libero_episode_index = 0
```

The primary interaction at each horizon remains:

```text
I_h =
  [S(OOD,+200,h) - S(OOD,Native,h)]
  -
  [S(ID,+200,h) - S(ID,Native,h)]
```

No additional delay or horizon may be introduced after outcomes are observed.

---

## 7. Shared-ID execution plan

Do **not** physically rerun identical ID controls separately for each
perturbation on the same base task.

The ID control depends on:

```text
task
horizon
delay
seed
```

not on which OOD perturbation it will later be contrasted against.

Therefore execute each unique ID control once and reuse it logically across the
candidate analyses for that same base task.

### Physical OOD episodes

```text
6 candidate pairs
× 3 horizons
× 2 delays
× 128 seeds
= 1,152 OOD episodes
```

### Physical ID episodes

```text
3 base tasks
× 3 horizons
× 2 delays
× 128 seeds
= 1,152 ID episodes
```

### Total new physical policy rollouts

```text
2,304 + 1,152 = 3,456 new episodes
```

For presentation, the six candidate-specific four-cell matrices contain:

```text
6 candidates × 3 horizons × 4 cells × 128
= 4,608 candidate-cell observations
```

but the shared ID rows are **references to the same physical episodes**. Never
duplicate them in an episode-level dataset and never count reused ID rows as
independent policy rollouts.

---

## 8. Initialization and matching rules

Use:

```text
libero_episode_index = 0
```

for every Stage 3 New rollout.

Stage 3C established that the selected LIBERO-Plus OOD variants do not expose
multiple distinct environment initializations through this interface. Therefore:

> `seed` is a rollout/policy stochasticity seed, not an environment-initialization
> identity.

### 8.1 Within-scene six-cell matching

For fixed:

```text
(task_key, scene_condition, exact_variant_identity, seed)
```

all six:

```text
{h20,h25,h30} × {Native,+200}
```

must use the same requested/resolved initialization index and the same initial
state fingerprint wherever benchmark semantics permit.

### 8.2 ID versus OOD

Do not require ID and OOD reset fingerprints to be equal when the perturbation
changes geometry or robot initial state.

Match ID and OOD on all non-treatment factors:

```text
base task
seed
libero_episode_index
checkpoint/revision
RTC implementation
control period
horizon
delay condition
preprocessing
action representation
runtime class where feasible
```

### 8.3 Shared goal-drawer ID controls

The same fresh `goal_drawer` ID episode is reused for:

```text
goal_drawer × object_layout
goal_drawer × robot_initial_state
goal_drawer × light_conditions
goal_drawer × sensor_noise
```

This reuse must be explicit in analysis provenance.

---

## 9. Primary statistical analysis

The point of Stage 3 New is **precision**, not significance fishing.

### 9.1 Per-cell reporting

For every candidate × horizon × scene × delay cell report:

```text
successes / 128
success proportion
Wilson 95% CI
```

### 9.2 Interaction estimate

For every candidate × horizon report:

```text
I_h
```

with a seed-cluster paired bootstrap 95% confidence interval.

Resample the **64 complete seed blocks**, not individual episode rows.

Each resampled seed block must carry all relevant:

```text
ID Native
ID +200
OOD Native
OOD +200
```

rows for the candidate and, when estimating an across-horizon contrast, all
three horizons for that seed.

Use at least:

```text
10,000 bootstrap replicates
```

and record the bootstrap RNG seed.

### 9.3 Primary operating point

The frozen main operating point remains:

```text
h = 25
delay contrast = Native versus +200 ms
```

The `h=20` and `h=30` rows remain the symmetric local-horizon robustness check.
Do not choose the horizon after inspecting Stage 3 New results.

### 9.4 Cross-task object-layout heterogeneity

For the three exact object-layout variants, report at each horizon:

```text
I_spatial(h)
I_goal(h)
I_long(h)
```

and paired-bootstrap contrasts:

```text
I_long(h) - I_spatial(h)
I_long(h) - I_goal(h)
```

Because the same seed block and shared ID design are used, preserve this
dependence in the bootstrap.

Do not infer task heterogeneity merely because one CI excludes zero and another
does not; examine the **difference between interaction estimates directly**.

### 9.5 Stage-3 candidate replication

Report all four Stage-3 candidate interactions, including the post-hoc
sensor-noise candidate.

Never relabel sensor noise as prespecified.

No candidate may be dropped because its high-replication estimate is
uninteresting.

---

## 10. Interpretation rules frozen before the run

Stage 3 New is allowed to **falsify** the current paper language.

### Outcome A — prior pattern survives with substantially tighter uncertainty

If `long_stove_moka × object_layout` remains materially negative while the
object-layout effects on the other two tasks and the other Stage-3 candidates
remain substantially closer to zero/non-negative, then the task-localized
interaction interpretation is strengthened.

Do not automatically call this a universal sequential-task effect.

### Outcome B — interactions shrink toward zero

If the high-replication interactions converge near zero with tight intervals,
then revise the paper to say:

> The apparent sparse/heterogeneous interactions in the low-replication screen
> were not stable under high-powered rerunning.

Do not preserve the old heterogeneity claim merely because some low-n signs
were negative.

### Outcome C — several interactions become reliably negative

Then the earlier screen understated the breadth of OOD × delay sensitivity.
Report the broader pattern without privileging the original
`long_stove_moka × object_layout` cell.

### Outcome D — direction changes across horizons

Then emphasize configuration dependence rather than a horizon-invariant
task/perturbation effect.

---

## 11. What is different from previous stages

| Experiment | Primary purpose | Replication | What changed |
|---|---|---:|---|
| Stage 1 | broad exploratory OOD screen | 5 seeds/cell | many tasks/perturbations; low replication |
| Stage 2 | temporal-coverage × delay operating envelope | 5 seeds/cell | ID-only mechanism study |
| Stage 3 | confirm selected Stage-1 candidates across nearby horizons | 8 seeds/cell | fresh rollouts, 4 candidate pairs |
| Stage 3B | test object-layout signal across the other Stage-1 tasks | 8 seeds/cell | targeted cross-task follow-up |
| Experiments A/B | layout/task generalization | 8 seeds/cell | additional layouts / second multi-stage task |
| **Stage 3 New** | **re-estimate the Stage 3/3B interaction matrix with high precision** | **128 completely fresh seeds/cell** | **no new scientific factor; only much larger replication** |

The key methodological sentence for the paper is:

> “Because the initial confirmatory matrices used eight stochastic rollouts per
> cell, we repeated the complete Stage 3/3B condition set using 128 entirely
> fresh rollout seeds per unique cell while holding tasks, variants, horizons,
> delay, policy, and execution semantics fixed.”

---

## 12. Required manifest

Create:

```text
stage3_new_manifest.csv
```

Each physical episode row must include at minimum:

```text
run_id
stage = stage_3_new_high_power_replication
seed
task_key
suite
base_task_id
base_task_name
candidate_key
candidate_original_status
scene_condition
perturbation_key
official_category
classification_id
api_task_index
variant_name
difficulty_level
n_action_steps
delay_condition
added_delay_ms
execution_method = rtc
libero_episode_index
requested_initialization_index
resolved_initialization_index
initial_state_fingerprint
model_revision
git_sha
libero_plus_git_sha
```

For ID rows:

```text
candidate_key = shared_id
perturbation_key = id
classification_id = null
api_task_index = null
variant_name = base task identity
```

The analysis join must map shared ID rows to each corresponding OOD candidate.

---

## 13. Required episode outputs

```text
stage3_new_manifest.csv
stage3_new_episode_results.csv
stage3_new_invalid_episodes.csv
stage3_new_initialization_pairing_audit.csv
stage3_new_four_cell_by_candidate_horizon.csv
stage3_new_interaction_by_candidate_horizon.csv
stage3_new_object_layout_cross_task_contrasts.csv
stage3_new_bootstrap_intervals.csv
stage3_new_preflight_environment.json
stage3_new_provenance.json
STAGE_3_NEW_OBSERVATIONS.md
```

Recommended figures:

```text
stage3_new_interaction_vs_horizon_all_candidates.png
stage3_new_object_layout_cross_task.png
stage3_new_low_n_vs_high_n_interactions.png
```

The low-n versus high-n plot may display Stage 3/3B estimates for historical
comparison, but the new primary estimates must use only seeds `46..109`.

---

## 14. Validation gates

Before any result is interpreted, assert:

```text
seeds == exactly 46..109
len(unique seeds) == 128
horizons == {20,25,30}
added_delay_ms == {0,200}
execution_method == rtc
libero_episode_index == 0
candidate set == exactly the six frozen candidate pairs above
```

Expected physical counts:

```text
OOD rows = 2,304
ID rows  = 1,152
total physical rows = 3,456
```

For every OOD candidate × seed:

```text
3 horizons × 2 delays = 6 OOD rows
```

For every base task × seed:

```text
3 horizons × 2 delays = 6 shared ID rows
```

Reject analysis if:

- a frozen variant identity does not match exactly;
- a required cell is missing;
- a seed is silently replaced;
- Native and +200 cells do not satisfy the reset-pairing audit;
- duplicate physical rows are counted as independent episodes;
- old Stage 3 / 3B episode rows are mixed into the primary Stage 3 New dataset.

---

## 15. Compute / resume requirements

This experiment is intentionally large:

```text
3,456 new physical policy episodes
```

The runner must support deterministic resume from a manifest.

After each completed episode, persist enough state that an interruption does not
change the seed-to-condition assignment.

Do not change the matrix because some cells run slowly or because interim
success rates look uninteresting.

If the compute window ends before completion:

1. preserve the partial archive;
2. do not select a favorable subset of candidate pairs or horizons;
3. report Stage 3 New as incomplete unless the entire predeclared primary
   `h=25` matrix has been completed for all six candidates and any reduced
   analysis is explicitly labeled as such.

The preferred outcome is the full frozen matrix.

---

## 16. Relation to OpenVLA stages

No additional OpenVLA policy experiments are planned.

Stage 4 remains historical provenance as an already completed preliminary
second-policy diagnostic.

Stage 5 is canceled before execution.

Stage 3 New supersedes Stage 5 as the active final experiment because the
highest-value remaining issue is uncertainty in the existing π0.5 interaction
estimates, not additional policy breadth.
