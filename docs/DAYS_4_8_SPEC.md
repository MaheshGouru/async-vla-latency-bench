# Days 4–8 Specification: Temporal Robustness Under Task Phase and Scene Change

**Team scope:** all three researchers  
**Prerequisite:** validated Days 1–3 harness and results  
**Primary policy:** the same pinned `lerobot/pi05_libero_finetuned` checkpoint  
**Required execution methods:** `ideal_sync`, `blocking_sync`, `naive_async`, `rtc`

Do not add LIBERO-Plus, VLASH, SmolVLA, FASTER, Reflex, VLA-Corrector, or a new
controller during Days 4–8.

---

## 1. Scientific objective

Extend the validated Days 1–3 benchmark to answer:

1. Does the same delay have different behavioral costs during transit, approach,
   precision, contact, and placement?
2. How many actions generated before a scene change execute afterward?
3. How long does stale control persist?
4. How long until the first action conditioned on a post-change observation
   executes?
5. Does RTC improve continuity, freshness, or both?

The minimum deliverable is a validated temporal-robustness study containing:

- task-phase labels;
- phase-conditioned delay injection;
- one reproducible mid-episode target displacement;
- stale-action and fresh-action reaction metrics;
- matched comparisons among required execution methods.

---

## 2. Entry requirements

Do not start broad experiments until these Days 1–3 outputs exist and pass
validation:

```text
async_vla_benchmark/outputs/environment.json
async_vla_benchmark/outputs/summaries/task_selection.csv
async_vla_benchmark/outputs/summaries/native_latency.csv
async_vla_benchmark/outputs/summaries/episodes.csv
async_vla_benchmark/outputs/summaries/requests.csv
async_vla_benchmark/outputs/summaries/horizon_sweep.csv
async_vla_benchmark/outputs/summaries/days1_3_report.md
```

Required implementation state:

- exact checkpoint loaded on CUDA;
- selected tasks recorded;
- request-specific latency used;
- latency-to-step conversion uses `ceil`;
- logical time does not use `sleep()`;
- observation, request, chunk, and action provenance exists;
- one-outstanding-request behavior is enforced;
- RTC receives the current delay and previous-chunk remainder;
- result validation passes.

Create:

```text
async_vla_benchmark/outputs/summaries/days1_3_audit.md
```

The audit must verify:

- repository and checkpoint revisions;
- task IDs and initial states;
- latency conversion;
- action-age calculation;
- queue semantics;
- RTC adapter inputs;
- paired seeds;
- missing or invalid runs.

Stop if a correctness failure can change the scientific conclusions.

---

## 3. Repository additions

Add to the existing benchmark:

```text
async_vla_benchmark/
├── configs/
│   ├── days4_8.yaml
│   ├── phase_pulses.yaml
│   └── interventions.yaml
├── benchmark/
│   ├── phases.py
│   ├── delay_pulses.py
│   ├── interventions.py
│   └── reaction_metrics.py
├── scripts/
│   ├── audit_days1_3.py
│   ├── run_phase_pulses.py
│   ├── run_dynamic_interventions.py
│   ├── validate_days4_8.py
│   └── make_days4_8_figures.py
└── outputs/
    ├── phase_pulses/
    ├── interventions/
    └── summaries/
```

Extend the existing execution engine and schemas. Do not build a second queue,
logical clock, or policy wrapper.

---

## 4. Team ownership

| Person | Primary ownership | Secondary responsibility |
|---|---|---|
| Person 1 | simulator geometry, object resolution, task phases, intervention and reset integrity | phase videos |
| Person 2 | delay pulses, provenance extensions, reaction metrics, experiment runner | log validation |
| Person 3 | aggregate analysis, confidence intervals, figures, report | independent semantics review |

All three review the Days 1–3 audit and the final decision gate.

---

## 5. Task selection

Use the exact task IDs selected during Days 1–3.

Required for phase-pulse study:

- selected LIBERO-Spatial task;
- selected LIBERO-Goal task.

Required for dynamic target displacement:

- selected LIBERO-Spatial task.

The selected LIBERO-10 task remains available for optional descriptive phase
analysis, but it is not required for the Days 4–8 run matrix.

Do not replace a task because an intervention result is inconvenient. Replace a
task only when the required geometry cannot be resolved or ideal success is
insufficient, and document the decision.

---

## 6. Privileged task-phase labels

Phase labels are for analysis and intervention timing only. They must never be
provided to the policy or alter observations.

Resolve:

- primary manipulated object;
- end-effector position;
- target contact;
- target grasp state;
- destination geometry where available.

Initial phase definitions:

```yaml
transit:
  condition: distance_to_target > 0.10 m and no target contact

approach:
  condition: 0.03 m < distance_to_target <= 0.10 m and no target contact

precision:
  condition: distance_to_target <= 0.03 m and no target contact

contact:
  condition: target contact is active and target is not yet stably grasped

placement:
  condition: target is grasped and is approaching or inside the destination region

unknown:
  condition: required geometry cannot be resolved
```

Thresholds are initial analysis settings, not universal constants. Record them
in config and do not tune them based on final outcomes.

Add to each executed-action row:

```text
task_phase
eef_target_distance_m
target_contact
target_grasped
destination_distance_m
phase_resolution_status
```

Validation:

- phase labels do not change the policy input;
- raw geometry is logged;
- unresolved phases become `unknown`;
- one video per selected task displays the phase and geometry;
- phase transitions are manually inspected.

Required output:

```text
outputs/summaries/phase_resolution.csv
```

---

## 7. Experiment A: phase-conditioned one-time delay pulse

### Purpose

Apply the same one-time latency increase during different phases while leaving
the rest of the episode at native latency.

### Methods

```text
naive_async
rtc
```

### Tasks

```text
selected LIBERO-Spatial
selected LIBERO-Goal
```

### Target phases

```text
transit
approach
precision_or_contact
```

For `precision_or_contact`:

1. trigger on the first request whose source observation is labeled `precision`;
2. if no such request occurs, trigger on the first request labeled `contact`;
3. if neither occurs, mark the episode invalid for this phase condition.

### Pulse

```yaml
normal_request_latency: measured native request latency
one_time_added_latency_ms: 700
maximum_pulses_per_episode: 1
```

The pulse must apply to the first request started in the requested phase.

Do not use `sleep()`.

Log:

```text
pulse_target_phase
pulse_triggered
pulse_request_id
pulse_request_step
pulse_source_observation_id
pulse_response_available_step
pulse_added_latency_ms
```

### Run matrix

```text
2 tasks
× 3 target phases
× 2 methods
× 5 paired seeds
= 60 episodes
```

Reuse no-pulse native controls from Days 1–3 only when every relevant
configuration field matches.

### Metrics

- task success;
- logical completion time;
- mean and maximum post-pulse action age;
- queue underrun steps;
- hold steps;
- discarded actions;
- action delta, acceleration, and jerk;
- time from pulse-source observation to first action from the delayed request;
- downstream episode success.

---

## 8. Experiment B: dynamic mid-chunk target displacement

### Purpose

Measure stale-action exposure after a scene change that occurs while old actions
remain buffered.

### Task

```text
selected LIBERO-Spatial task
```

### Trigger

```text
first transition into approach
```

### Default intervention

```yaml
name: target_shift_5cm
translation_m: 0.05
preferred_axis: world_x
preserve_height: true
preserve_orientation: true
zero_linear_velocity: true
zero_angular_velocity: true
```

If positive x is invalid, use negative x. Record the actual displacement vector.

### Intervention semantics

At intervention time:

- do not clear the queue;
- do not cancel an in-flight request;
- do not issue an immediate extra request;
- do not alter method-specific request timing;
- do not move an already grasped object;
- do not silently move the trigger to a later phase.

An episode is invalid for reaction analysis when:

- the target cannot be resolved;
- the target is already grasped;
- neither displacement direction is workspace-safe;
- the intervention produces an invalid collision or simulator failure.

Invalid episodes remain logged and are excluded only from reaction aggregates.

### Conditions

```text
ideal_sync:
  ideal logical latency

blocking_sync:
  native_plus_700

naive_async:
  native
  native_plus_700

rtc:
  native
  native_plus_700
```

### Run matrix

```text
ideal_sync:      1 condition × 5 seeds = 5
blocking_sync:   1 condition × 5 seeds = 5
naive_async:     2 conditions × 5 seeds = 10
rtc:             2 conditions × 5 seeds = 10

total = 30 episodes
```

---

## 9. Canonical reaction metrics

Let the intervention occur at logical time `t_i`.

### Stale action

An action is stale when:

```text
action_execution_time >= t_i
and
source_observation_time < t_i
```

### Stale-action count

```text
N_stale = number of stale actions executed after t_i
```

### Stale duration

```text
T_stale =
  last stale-action execution time - t_i
```

Use zero when no stale action executes.

### Fresh-action reaction latency

```text
T_fresh =
  first execution time of an action whose source observation was captured
  after t_i
  -
  t_i
```

Do not substitute:

- inference completion;
- response arrival;
- queue insertion;
- first action from an already in-flight pre-intervention request.

### Required fields

```text
intervention_id
intervention_step
intervention_logical_time
intervention_displacement_xyz
first_post_intervention_observation_id
first_post_intervention_request_id
first_fresh_action_step
stale_action_count
stale_duration_ms
fresh_action_reaction_latency_ms
recovery_success
intervention_valid
invalid_reason
```

---

## 10. Required tests

### Phase tests

- phase labels do not modify policy inputs;
- raw distance/contact values are recorded;
- `unknown` is used when geometry cannot be resolved;
- phase pulse occurs once;
- phase pulse occurs in the configured phase;
- invalid phase conditions are not silently reassigned.

### Intervention tests

- target moves approximately 5 cm;
- height and orientation are preserved;
- linear and angular velocity reset;
- queue contents are not cleared;
- outstanding request is not canceled;
- reset restores the original scene;
- intervention does not leak into the next episode.

### Reaction tests

- pre-intervention source observations are classified stale;
- post-intervention source observations are classified fresh;
- response arrival is not mistaken for action execution;
- invalid intervention episodes are excluded from reaction aggregates;
- stale count and duration are zero when no stale action executes.

---

## 11. Required outputs

Raw and episode-level outputs should extend the existing Days 1–3 format.

Required summaries:

```text
outputs/summaries/days1_3_audit.md
outputs/summaries/phase_resolution.csv
outputs/summaries/phase_pulse_results.csv
outputs/summaries/intervention_results.csv
outputs/summaries/reaction_metrics.csv
outputs/summaries/days4_8_report.md
```

Required figures:

```text
outputs/figures/success_by_pulse_phase.png
outputs/figures/action_age_by_pulse_phase.png
outputs/figures/pulse_request_to_execution.png
outputs/figures/stale_actions_after_intervention.png
outputs/figures/stale_duration_after_intervention.png
outputs/figures/fresh_action_reaction_latency.png
outputs/figures/continuity_vs_freshness.png
outputs/figures/intervention_timeline_examples.png
```

Required videos:

- one phase-annotated episode per selected task;
- one representative intervention episode per method;
- every intervention infrastructure failure.

---

## 12. Statistical reporting

Use paired seeds and identical initial states wherever possible.

For success:

- raw success count;
- success rate;
- Wilson 95% interval.

For continuous metrics:

- mean;
- median;
- bootstrap 95% interval over episodes.

Report paired method differences for matched seeds.

Five-seed results are preliminary. Do not treat per-step actions as independent
episode samples.

---

## 13. Day-by-day plan

### Day 4

- run Days 1–3 audit;
- implement object and geometry resolution;
- implement phase labels;
- generate and inspect phase videos;
- implement one-time pulse infrastructure.

### Day 5

- complete phase-label tests;
- run phase-pulse smoke tests;
- verify pulse timing and provenance;
- begin the 60-episode phase matrix.

### Day 6

- finish phase-pulse matrix;
- implement target displacement;
- complete intervention and reset tests;
- add reaction metric extraction.

### Day 7

- run the 30-episode dynamic-intervention matrix;
- validate fresh/stale classification;
- rerun infrastructure failures;
- generate representative videos.

### Day 8

- validate all Days 4–8 outputs;
- aggregate metrics;
- generate figures;
- write `days4_8_report.md`;
- apply decision gate.

---

## 14. Commands

Provide commands resembling:

```bash
python async_vla_benchmark/scripts/audit_days1_3.py \
  --output-dir async_vla_benchmark/outputs

python async_vla_benchmark/scripts/run_phase_pulses.py \
  --config async_vla_benchmark/configs/days4_8.yaml \
  --dry-run

python async_vla_benchmark/scripts/run_phase_pulses.py \
  --config async_vla_benchmark/configs/days4_8.yaml \
  --resume

python async_vla_benchmark/scripts/run_dynamic_interventions.py \
  --config async_vla_benchmark/configs/days4_8.yaml \
  --resume

python async_vla_benchmark/scripts/validate_days4_8.py \
  --output-dir async_vla_benchmark/outputs

python async_vla_benchmark/scripts/make_days4_8_figures.py \
  --output-dir async_vla_benchmark/outputs
```

Support:

```text
--dry-run
--resume
--task
--seed
--strategy
--latency-profile
--phase
--overwrite
```

---

## 15. Decision gate

Continue to Week 2 when at least one core temporal-robustness effect is
reproducible:

- delay effects differ by task phase;
- dynamic intervention produces nonzero stale-action exposure;
- RTC improves continuity but leaves a measurable freshness gap;
- action age reveals behavior not explained by request latency.

Stop or reframe when:

- phase labels are unreliable;
- dynamic interventions cannot be reproduced;
- target movement creates no stale-action exposure;
- all methods produce effectively identical temporal behavior;
- ideal success is too low to isolate delay effects;
- the result is only “more delay reduces success.”

---

## 16. Stage report questions

`days4_8_report.md` must answer:

1. Did identical delay have different effects by phase?
2. Which phase was least delay-tolerant?
3. How many stale actions executed after target movement?
4. How long did stale control persist?
5. What was fresh-action reaction latency?
6. Did blocking avoid stale actions at the cost of completion speed?
7. Did RTC improve continuity?
8. Did RTC improve freshness?
9. Were action age and request latency meaningfully different?
10. Is the temporal-robustness signal strong enough for the LIBERO-Plus study?
