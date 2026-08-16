# Metrics and Logging Specification

This file defines canonical terms for Stage 0, Stage 1, and Stage 2.

## 1. Time bases

### Wall-clock time

Measure with a monotonic clock.

Record:

```text
preprocessing_latency_ms
model_latency_ms
postprocessing_latency_ms
request_latency_ms
wall_clock_episode_s
```

### Logical control time

```text
logical_time = control_step × control_period
```

Use logical time for simulated response availability, queue behavior, execution, and action age.

Artificial delay must use the logical clock. Do **not** use `sleep()` to model control delay.

## 2. Request latency

```text
request_latency =
  response_complete_wall_time
  -
  observation_capture_wall_time
```

Report mean, p50, p95, and where useful p99.

## 3. Added delay

```text
total_logical_latency_ms =
  measured_request_latency_ms
  +
  added_delay_ms
```

Stage 0 tests:

```text
0, 100, 200, 300, 400 ms
```

The original `500–700 ms` extension was dropped after the ID-only run provided
sufficient non-saturated calibration evidence by `400 ms`. This revision was
made before Stage 1 OOD outcomes.

Stage 1 and Stage 2 use:

```text
Low  = Native          = added_delay_ms = 0
High = Native + d*     = added_delay_ms = selected_high_delay_ms
```

## 4. Logical delay

```text
delay_steps =
  ceil(total_logical_latency_ms / control_period_ms)
```

Record request-specific delay. Do not replace it with a single mean latency.

## 5. Action age

For each executed action:

```text
action_age =
  action_execution_logical_time
  -
  source_observation_logical_time
```

This is the primary temporal-freshness diagnostic.

Episode aggregates:

```text
action_age_mean_ms
action_age_p50_ms
action_age_p95_ms
action_age_max_ms
```

## 6. Queue behavior

Record:

```text
queue_depth_before
queue_depth_after
queue_occupancy_mean
queue_occupancy_p95
is_hold
is_underrun
discard_count
```

Definitions:

- `hold`: configured hold action executes.
- `underrun`: no policy action is available when an action is required.
- Do not automatically equate intentional holds with queue underruns.

## 7. Continuity

On robot-motion dimensions, calculate consistently:

```text
action_delta
action_acceleration
action_jerk
```

Document the norm and finite-difference convention once. Treat continuity as secondary.

## 8. Success

Primary outcome:

```text
success ∈ {0,1}
```

Also record:

```text
episode_steps
completion_fraction
failure_mode
```

Do not replace success with per-step proxies.

## 9. OOD × delay interaction

For matched task, perturbation, and method:

```text
I =
  [S(OOD, high) - S(OOD, low)]
  -
  [S(ID, high) - S(ID, low)]
```

Interpretation:

```text
I < 0   OOD reduces delay tolerance
I ≈ 0   delay penalty is similar under ID and OOD
I > 0   delay appears less damaging under OOD; inspect floors/noise carefully
```

Do not interpret `I` when OOD-low or ID-low is at a severe floor.

## 10. Canonical taxonomy fields

Every episode must include both machine keys and display labels.

```text
task_group_key
task_group_label

perturbation_key
perturbation_label

mechanism_group_key
mechanism_group_label
```

Display labels must be exactly:

```text
Single-stage transport
Articulated/contact-rich
Multi-stage/sequential

Trajectory adaptation
Perceptual localization
Appearance invariance
Semantic grounding
```

## 11. Required episode identity

```text
run_id
stage
git_sha
libero_plus_git_sha
model_revision
task_key
suite
base_task_id
base_task_name
task_group_key
task_group_label
scene_condition
perturbation_key
perturbation_label
official_category
mechanism_group_key
mechanism_group_label
classification_id
api_task_index
variant_name
difficulty_level
execution_method
delay_condition
added_delay_ms
selected_high_delay_ms
seed
n_action_steps
environment_fingerprint
gpu_id
```

For ID rows, OOD-only fields may be null.

## 12. Observation → request → chunk → action provenance

### Observation

```text
observation_id
episode_id
control_step
logical_time
wall_time
```

### Request

```text
request_id
source_observation_id
request_step
preprocess_ms
model_ms
postprocess_ms
request_ms
added_delay_ms
delay_steps
response_available_step
method
```

### Chunk

```text
chunk_id
request_id
source_observation_id
chunk_length
availability_step
method
```

### Executed action

```text
episode_id
control_step
execution_logical_time
action_vector
chunk_id
chunk_action_index
source_observation_id
source_observation_step
action_age_steps
action_age_ms
queue_depth_before
queue_depth_after
is_hold
is_underrun
```

## 13. Provenance invariants

Fail validation when:

- an executed action does not reference a chunk;
- a chunk does not reference a request;
- a request does not reference an observation;
- timestamps are non-monotonic;
- action age is negative;
- environment fingerprint is missing;
- checkpoint revision is missing;
- method is missing;
- Stage 1 uses a high delay different from `selected_high_delay.json`.

## 14. Statistical reporting

### Exploratory Stage 1

Always report:

- raw successes / trials;
- all four ID/OOD × low/high cells;
- `I`;
- null results;
- invalid/missing runs.

Do not describe a 5-seed exploratory cell as statistically significant without an appropriate prespecified analysis and uncertainty estimate.

### Confirmatory Stage 2

Report:

- raw counts;
- Wilson intervals for success;
- paired differences where seeds are matched;
- bootstrap intervals for interaction/effect differences where appropriate;
- effect sizes;
- no per-step pseudoreplication.

Primary interaction model when sample size supports it:

```text
logit P(success) =
  β0
  + β1 OOD
  + β2 HighDelay
  + β3 OOD×HighDelay
```

For method comparison, extend with `Method` and the corresponding interactions. The OOD × HighDelay term is the primary interaction quantity; the three-way interaction asks whether the execution method changes it.

## 15. Failure-mode labels

Use only:

```text
success
perception_localization
approach_alignment
grasp_failure
contact_execution
trajectory_recovery
wrong_subgoal_or_semantics
sequential_error_accumulation
timeout
other
```

Failure labels are descriptive and should not be treated as ground-truth model cognition.
