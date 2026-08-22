# Stage 4 — Second-Policy Replication with OpenVLA-OFT

## 0. Status and scientific purpose

**Status: NEW / RUN NEXT ONLY IF THERE IS TIME AFTER THE completed π0.5 experiments.**

Stages 1–3B and Experiments A/B establish the current π0.5 result:

- temporal action coverage strongly controls delay robustness;
- there is no broad OOD × delay amplification;
- the surviving `long_stove_moka × object_layout` interaction is task- and layout-dependent;
- Experiment A reproduced a negative interaction in 2/3 new layouts (`mean I=-0.125`);
- Experiment B reproduced a negative interaction in only 1/3 layouts on the second multi-stage task (`mean I=+0.167`).

The largest remaining external-validity limitation is that all primary experiments use one VLA policy.

Stage 4 asks one narrow question:

> Does the qualitative OOD × delay pattern appear under a second, architecturally different VLA policy executed asynchronously?

Stage 4 is **not** an RTC replication. OpenVLA-OFT does not use the π0/π0.5 RTC guidance path. It is evaluated with the benchmark's naive asynchronous queue semantics and its native 8-action chunk.

Do not describe Stage 4 as a controlled causal comparison of model architecture. Policy, native action coverage, and policy-compatible execution differ. It is a second-policy external-validity diagnostic.

## 1. Frozen policy

Use exactly:

```text
policy_family       = OpenVLA-OFT
checkpoint_id       = moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10
checkpoint_revision = 13cdacd486c504e65408fc3c9e12fec9c5bf0382
openvla_oft_repo    = moojink/openvla-oft
openvla_oft_commit  = e4287e94541f459edc4feabc4e181f537cd569a8
```

Use the combined four-suite checkpoint rather than four suite-specific checkpoints so the second-policy experiment uses one frozen model across both tasks.

Required upstream evaluation settings:

```text
use_l1_regression   = true
use_diffusion       = false
use_film            = false
num_images_in_input = 2
use_proprio         = true
center_crop         = true
load_in_8bit        = false
load_in_4bit        = false
native_chunk_size   = 8
```

The combined checkpoint's OFT L1 action head must be the checkpoint-associated 300k-step head loaded by the official OpenVLA-OFT utilities. Use the upstream LIBERO action un-normalization logic; record the resolved `unnorm_key` for every task.

For reproducibility, use the upstream-reported LIBERO software regime where feasible:

```text
Python       = 3.10.14
PyTorch      = 2.2.0
Transformers = OpenVLA-OFT custom v4.40.1 fork
GPU          = NVIDIA A100
```

**Dispatch blocker:** log the resolved model snapshot/revision, OpenVLA-OFT git SHA, action-head identity, processor identity, and runtime package versions before any analysis rollout.

## 2. Frozen tasks

Use exactly two diagnostic tasks.

### 2.1 Prior null-interaction task

```text
task_key       = spatial_transport
suite          = libero_spatial
base_task_id   = 2
base_task_name = pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate
```

### 2.2 Prior negative-interaction task

```text
task_key       = long_stove_moka
suite          = libero_10
base_task_id   = 2
base_task_name = KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it
```

Rationale:

- `spatial_transport × object_layout` was null under π0.5 across Stage-3B horizons;
- `long_stove_moka × object_layout` was negative under π0.5 across all Stage-3 horizons and was the only task with a consistently negative cross-task object-layout signal;
- using one prior-null and one prior-negative task is the smallest diagnostic second-policy matrix;
- do not add the Experiment-B task unless this Stage-4 matrix is already complete.

## 3. Frozen perturbation and exact OOD variants

Use **Objects Layout only**.

```text
perturbation_key  = object_layout
official_category = Objects Layout
mechanism_group   = trajectory_adaptation
```

Use the exact original frozen Stage-1/Stage-3B variants below. These variants were selected before the later Experiment-A/B outcomes, avoiding outcome-adaptive layout selection.

| task | `classification_id` | `api_task_index` | difficulty | exact `variant_name` |
|---|---:|---:|---:|---|
| `spatial_transport` | `1773` | `1772` | `3` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15` |
| `long_stove_moka` | `1941` | `1940` | `2` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25` |

Before dispatch, assert literal equality of:

```text
task_key
suite
base_task_id
base_task_name
classification_id
api_task_index
difficulty_level
variant_name
official_category == "Objects Layout"
```

Do not select a different layout because OpenVLA-OFT performs better or worse on a frozen variant.

## 4. Frozen execution method

Stage 4 uses **naive asynchronous execution**, not RTC.

```text
execution_method          = naive_async_openvla_oft
control_rate_hz           = 20
control_period_ms          = 50
native_chunk_size         = 8
configured_action_coverage= 8 actions
request_threshold_actions = 4
delay_conditions          = [Native, Native+200ms]
added_delay_ms            = [0, 200]
libero_episode_index      = 0
```

`request_threshold_actions=4` is frozen as `ceil(8/2)`, matching the benchmark's existing half-horizon asynchronous request rule.

Do **not** increase the threshold, repeat actions, concatenate multiple OpenVLA-OFT chunks, stretch actions in time, or synthesize a 25-action horizon to make the policy resemble π0.5.

### 4.1 Exact latency semantics

For every policy request:

```text
measured_request_latency_ms =
    observation capture
  + preprocessing
  + model inference
  + postprocessing

total_logical_latency_ms =
    measured_request_latency_ms
  + added_delay_ms

delay_steps =
    ceil(total_logical_latency_ms / 50 ms)

response_available_step =
    source_observation_step + delay_steps
```

While the new request is logically unavailable:

1. execute the remaining actions from the previous OpenVLA-OFT chunk;
2. if the queue empties, execute the benchmark hold action and mark a queue underrun;
3. when the new response becomes available, replace the queue with the returned 8-action chunk.

Because this is not RTC:

```text
inference_delay is NOT passed into OpenVLA-OFT
previous-chunk guidance is NOT used
returned actions are NOT sliced by delay_steps
```

The first returned action is executed when the asynchronously delayed chunk becomes available. Its staleness is measured through action age.

### 4.2 Startup

Use the same ideal-startup convention as the existing naive-async benchmark:

- obtain one initial OpenVLA-OFT chunk without added/native logical delay;
- seed the 8-action queue;
- then enable the frozen Native or Native+200-ms profile for all subsequent requests.

The startup request must be labeled and excluded from paper-facing request-latency and delay-estimation summaries where the earlier pipeline excludes startup.

## 5. Frozen seeds

Use exactly:

```text
SEEDS = [38,39,40,41,42,43,44,45]
```

These seeds have not been used in Stages 0–3B or Experiments A/B.

Use the same eight seeds in every task × scene × delay cell.

These are rollout/policy stochasticity seeds at the benchmark-provided fixed initialization. They are **not** eight environment initializations.

Do not substitute seeds after failures or expand the seed set after inspecting outcomes.

Infrastructure-corrupted episodes may rerun only with the identical physical tuple and seed.

## 6. Initialization and pairing

Use exactly:

```text
libero_episode_index = 0
```

for ID and OOD.

Stage 3C established that the frozen LIBERO-Plus object-layout variants expose only one distinct OOD initialization. Therefore do not attempt indices 1–7.

For every fixed:

```text
(task_key, scene_condition, exact_variant_or_ID, seed)
```

the Native and +200-ms rows must have:

```text
same requested initialization index
same resolved initialization index
same initial_state_fingerprint
same policy/checkpoint revision
same action-head/processor configuration
same action coverage and request threshold
same environment/runtime configuration
```

ID and OOD fingerprints are not required to match because object layout intentionally changes scene geometry.

## 7. Exact physical episode matrix

Per task:

```text
ID:
    1 ID scene × 2 delays × 8 seeds = 16 episodes

OOD:
    1 exact frozen object-layout variant × 2 delays × 8 seeds = 16 episodes

total per task = 32 episodes
```

Across two tasks:

```text
2 tasks × 2 scenes × 2 delays × 8 seeds = 64 physical analysis episodes
```

Exact accounting:

```text
spatial_transport ID   = 16
spatial_transport OOD  = 16
long_stove_moka ID     = 16
long_stove_moka OOD    = 16
--------------------------------
TOTAL                   = 64
```

No π0.5 episode may be counted as a Stage-4 physical row.

## 8. Smoke test outside the analysis manifest

Before seeds 38–45, run exactly four seed-999 smoke episodes:

```text
spatial_transport / ID  / Native / seed999
spatial_transport / OOD / Native / seed999
long_stove_moka   / ID  / Native / seed999
long_stove_moka   / OOD / Native / seed999
```

These four episodes are **not** part of the 64-row analysis matrix.

Smoke gate checks implementation validity, not scientific success:

```text
policy loads at exact revision
action head and proprio projector load
center crop and two-image observation path are active
action output shape is 8 × 7
actions are finite
LIBERO gripper conversion is correct
ID and OOD environments reset successfully
request/action artifacts are complete
logical response timing is recorded
```

A task failure is allowed in smoke. An exception, malformed action, missing artifact, wrong OOD variant, or incorrect model revision fails the smoke gate.

## 9. Required provenance artifacts

Create:

```text
stage4_second_policy_manifest.csv
stage4_episode_results.csv
stage4_invalid_episodes.csv
stage4_initialization_pairing_audit.csv
stage4_preflight_environment.json
stage4_smoke_validation.json
stage4_policy_provenance.json
stage4_analysis_four_cell_by_task.csv
stage4_analysis_interaction_by_task.csv
STAGE_4_OBSERVATIONS.md
```

Every analysis row must contain at minimum:

```text
stage_or_experiment_label = stage4_second_policy
policy_family = openvla_oft
checkpoint_id
checkpoint_revision
openvla_oft_git_sha
action_head_identity
processor_identity
resolved_unnorm_key
task_key
suite
base_task_id
base_task_name
scene_condition
classification_id
api_task_index
variant_name
rollout_seed
requested_initialization_index
resolved_initialization_index
initial_state_fingerprint
execution_method
configured_action_coverage
request_threshold_actions
native_chunk_size
added_delay_ms
measured_request_latency_ms
total_logical_latency_ms
logical_delay_steps
mean_action_age_ms
p95_action_age_ms
queue_underrun_steps
hold_action_steps
success
status
manifest_sha256
spec_sha256
git_sha
```

## 10. Validation gates

Before analysis, require:

```text
analysis rows = 64 exactly
tasks = {spatial_transport,long_stove_moka} exactly
rows per task = 32 exactly
ID rows = 32 exactly
OOD rows = 32 exactly
delays = {0,200} exactly
seeds = {38,39,40,41,42,43,44,45} exactly
policy_family = {openvla_oft} exactly
execution_method = {naive_async_openvla_oft} exactly
native_chunk_size = {8} exactly
configured_action_coverage = {8} exactly
request_threshold_actions = {4} exactly
requested initialization = {0} exactly
resolved initialization = {0} exactly
unique physical tuples = 64 exactly
```

For each `(task, scene, exact_variant_or_ID, seed)`, Native and +200 must share the same initialization fingerprint.

Do not fail validation merely because a scientific episode has `success=false` or contains genuine queue underruns. Those are outcomes.

Do fail validation for incomplete artifacts, wrong checkpoint, wrong variant identity, malformed actions, initialization mismatch within a delay pair, or timing/provenance corruption.

## 11. Primary analysis

For each task independently compute:

```text
I_task =
    [S(OOD,+200)-S(OOD,Native)]
  - [S(ID,+200)-S(ID,Native)]
```

Report all four raw cells as `successes/8`.

Use an eight-cluster paired bootstrap:

- resample seeds `[38..45]` with replacement;
- carry ID Native, ID +200, OOD Native, and OOD +200 for that seed together;
- report the 95% bootstrap interval for `I_task`.

Primary figure:

```text
task                 ID Native   ID +200   OOD Native   OOD +200   I_task
spatial_transport       x/8        x/8        x/8          x/8       ...
long_stove_moka         x/8        x/8        x/8          x/8       ...
```

Secondary diagnostics:

```text
native request latency by task
total logical delay steps
mean/p95 action age
queue-underrun steps
hold-action fraction
success versus realized coverage ratio
```

## 12. Cross-policy interpretation

The completed π0.5 reference pattern at the central Stage-3B horizon is:

```text
spatial_transport × object_layout: I_25 = 0.000
long_stove_moka × object_layout:   I_25 = -0.250
```

Use this only as a **qualitative reference**, not a paired statistical comparison.

Pre-frozen interpretations:

### If OpenVLA-OFT is also approximately null on spatial and negative on long

State:

> The task-dependent contrast is qualitatively reproduced under a second VLA and a different policy-compatible asynchronous execution stack.

Do not claim architecture-independent universality.

### If both OpenVLA-OFT interactions are null/non-negative

State:

> The localized π0.5 OOD × delay pattern does not transfer to the second policy/execution stack, indicating limited cross-policy external validity.

### If both are strongly negative

State:

> OpenVLA-OFT shows broader OOD × delay sensitivity than π0.5 in this diagnostic subset; examine whether shorter native temporal coverage and queue underruns account for the difference.

### If Native OpenVLA-OFT already suffers severe queue starvation

Do not hide or retune it. Report:

> The policy's native 8-action temporal coverage is insufficient relative to measured request latency under the benchmark's 20-Hz asynchronous controller.

This directly bears on the paper's temporal-action-coverage result.

## 13. Prohibited adaptations

After any Stage-4 outcome is observed, do not:

- change the two tasks;
- change the exact OOD variants;
- replace +200 ms with an easier delay;
- alter the eight analysis seeds;
- change `request_threshold_actions=4`;
- concatenate chunks to manufacture a longer horizon;
- add RTC-like guidance to OpenVLA-OFT;
- discard difficult variants;
- rerun genuine task failures with replacement seeds;
- call the Stage-4 seeds distinct environment initializations.

Any later modification is a separately labeled exploratory experiment and must not overwrite Stage 4.

## 14. Paper role

Stage 4 is intentionally small.

Its role is to address:

> Are the paper's temporal-robustness observations specific to π0.5?

It is **not** intended to repeat the seven-family Stage-1 screen or the full Stage-2 horizon × latency grid.

If Stage 4 completes cleanly, the paper can truthfully say that the central evaluation was additionally tested on a second VLA policy. The exact strength of the cross-policy claim must follow the observed Stage-4 outcomes.
