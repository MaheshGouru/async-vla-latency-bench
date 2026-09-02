# Metrics and Logging Specification

This file defines canonical terms for Stages 0–4.

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

Stage 1 uses:

```text
Low  = Native          = added_delay_ms = 0
High = Native + d*     = added_delay_ms = selected_high_delay_ms
```

Stage 2 local sensitivity uses the explicitly labeled added-delay values:

```text
Native (0), 100, 200, 300 ms
```

Native is a measured-latency condition with `added_delay_ms=0`, not an ideal or
zero-request-latency condition. It is required at every Stage 2 horizon.

Stage 3 returns to the frozen Stage 1 comparison:

```text
Low  = Native
High = Native + 200 ms
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

### Post-hoc sensitivity Stage 2

Report the complete frozen local grid, raw counts, uncertainty, and normalized
coverage diagnostics. Do not call Stage 2 confirmatory and do not use it to
retroactively redefine the Stage 1 operating point.

### Confirmatory Stage 3

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


## 16. Horizon × latency fields

Stages 2 and 3 add:

```text
configured_n_action_steps
prediction_horizon_actions
control_period_ms
added_delay_steps
total_logical_delay_steps
coverage_ratio_added
coverage_ratio_total
rtc_frozen_prefix_steps
rtc_guided_overlap_steps
rtc_fresh_suffix_steps
previous_chunk_remaining_at_request
previous_chunk_remaining_at_response
```

Definitions:

```text
coverage_ratio_added =
    added_delay_steps / configured_n_action_steps

coverage_ratio_total =
    total_logical_delay_steps / configured_n_action_steps
```

Do not call `configured_n_action_steps` RTC execution horizon `s` unless adapter
inspection proves equivalence.

## 17. Horizon-conditioned OOD interaction

```text
I_h =
  [S(OOD, high, h) - S(OOD, low, h)]
  -
  [S(ID, high, h) - S(ID, low, h)]
```

Also report:

```text
ΔI_10→25 = I_25 - I_10
```

Do not interpret interactions at severe baseline floors.

## 18. Experimental-status labels

Every post-Stage-1 result must include:

```text
analysis_status ∈ {
    exploratory,
    posthoc_sensitivity,
    prespecified_confirmatory,
    posthoc_replication,
    conditional_method_validation
}
```

Stage 2 local operating-point analysis is `posthoc_sensitivity`.
Sensor noise is `posthoc_replication`.


## 19. Stage 2 baseline-normalized sensitivity

Because Stage 2 contains Native at every tested `n_action_steps`, report:

```text
native_success(h) = S(h, Native)

delay_drop_100(h) = S(h,+100) - S(h,Native)
delay_drop_200(h) = S(h,+200) - S(h,Native)
delay_drop_300(h) = S(h,+300) - S(h,Native)
```

This separates the main effect of configured action coverage from the incremental
effect of added delay.

Use the same Stage 2 seeds `[5,6,7,8,9]` in every cell.


## 20. Episode identity and cross-condition pairing

All post-Stage-1 manifests must log:

```text
task_key
suite
base_task_id
base_task_name
seed
initialization_index_or_id
initial_state_fingerprint
scene
perturbation_key
classification_id
api_task_index
variant_name
difficulty_level
```

For ID rows, perturbation-specific identifiers are null.

### Stage 2 pairing key

```text
(task_key, seed)
```

All horizon × delay cells must share the same initialization identity.

### Stage 3 pairing key

```text
(task_key, variant_name, seed, scene)
```

All `{20,25,30} × {Native,+200}` cells must share the same initialization identity
where benchmark semantics permit.

Do not interpret seed equality alone as proof of identical initialization. Validate
or fingerprint the reset state.


## Stage 3C initialization-audit fields

Stage 3C contains reset-only records. Log at minimum:

```text
task_key
scene_condition
variant_name_or_id
requested_initialization_index
resolved_initialization_index_or_id
repeat_id
initial_state_fingerprint
fingerprint_schema_version
stage3c_spec_hash
```

No success, action-age, RTC, or policy-inference metrics belong to Stage 3C.


## 21. Stage 4 second-policy fields

Stage 4 uses OpenVLA-OFT and naive asynchronous execution rather than RTC. Log:

```text
policy_family
checkpoint_id
checkpoint_revision
openvla_oft_git_sha
action_head_identity
processor_identity
resolved_unnorm_key
native_chunk_size
configured_action_coverage
request_threshold_actions
added_delay_ms
measured_request_latency_ms
total_logical_latency_ms
logical_delay_steps
mean_action_age_ms
p95_action_age_ms
queue_underrun_steps
hold_action_steps
success
```

Frozen Stage-4 values:

```text
policy_family = openvla_oft
native_chunk_size = 8
configured_action_coverage = 8
request_threshold_actions = 4
added_delay_ms ∈ {0,200}
seeds = 38..45
```

Do not emit RTC guidance fields as if they were meaningful for OpenVLA-OFT. They must be null/not-applicable.

Primary Stage-4 interaction per task:

```text
I_task =
  [S(OOD,+200)-S(OOD,Native)]
  -
  [S(ID,+200)-S(ID,Native)]
```

Report all four raw `successes/8` cells and an eight-seed paired-bootstrap interval.


## 22. Stage 5 coverage-calibration fields

In addition to Stage-4 fields, record:

```text
model_native_output_horizon
configured_action_coverage
coverage_is_single_inference_native
request_threshold_actions
realized_coverage_ratio
coverage_candidate_set_hash
coverage_selection_status
```

Stage 5A must contain ID scenes only and seeds `46..50`. Stage 5B, if run, uses the frozen Stage-5A coverage and fresh seeds `51..58`.

## Stage 3 New — high-power replication metrics

Primary success metric remains binary episode success.

Required Stage 3 New analysis identity:

```text
stage = stage_3_new_high_power_replication
candidate_key
candidate_original_status
seed
task_key
scene_condition
perturbation_key
classification_id
api_task_index
variant_name
n_action_steps
delay_condition
added_delay_ms
execution_method
```

Fresh seed block:

```text
46..81 inclusive
n = 36
```

For every candidate and horizon:

```text
I_h =
  [S(OOD,+200,h)-S(OOD,Native,h)]
  -
  [S(ID,+200,h)-S(ID,Native,h)]
```

Report:

```text
successes / 36
Wilson 95% CI for every success proportion
I_h
seed-cluster paired-bootstrap 95% CI for I_h
```

Bootstrap the complete seed block. Do not bootstrap the four cells
independently.

For the three object-layout task conditions also report direct paired-bootstrap
heterogeneity contrasts:

```text
I_long - I_spatial
I_long - I_goal
```

at each of `h={20,25,30}`.

The same physical shared-ID row may participate in several candidate-level
contrasts. This reuse must remain explicit; it does not create additional
independent episode observations.

Old Stage 3/3B rows may appear in a historical comparison plot but must not be
included in the primary Stage 3 New point estimates or confidence intervals.
