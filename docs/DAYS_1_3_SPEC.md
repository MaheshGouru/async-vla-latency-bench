You are an autonomous coding agent working inside VS Code. Implement a focused three-day feasibility benchmark for asynchronous buffering with π0.5 on LIBERO.

Do not train or fine-tune a model. Do not implement OOD perturbations, dynamic object movement, VLASH, FASTER, DEHP, AAC, SmolVLA, or OpenVLA in this task.

The required baselines are:

1. Ideal and blocking synchronous execution.
2. Naive asynchronous action queue.
3. Real-Time Chunking, or RTC.
4. Fixed execution-horizon sweep.

# 1. Scientific objective

Build a reproducible evaluation harness that answers:

1. What is the native end-to-end inference latency of π0.5-LIBERO?
2. How does that latency translate into action age measured in control steps and milliseconds?
3. How much do synchronous blocking, naive asynchronous buffering, and RTC differ in:

   * task success;
   * queue underruns;
   * action staleness;
   * task completion time;
   * action continuity?
4. Can the effects be explained by choosing a better fixed execution horizon?

The central comparison is:

```text
ideal_sync
blocking_sync
naive_async
rtc
```

The fixed-horizon sweep must be run for `naive_async` and `rtc`.

# 2. Required software, checkpoint, and dataset

Use:

```yaml
repository: huggingface/lerobot
policy_checkpoint: lerobot/pi05_libero_finetuned
dataset_repo: HuggingFaceVLA/libero
environment: LIBERO through LeRobot
device: cuda
mujoco_backend: egl
policy_n_action_steps: 10
policy_num_inference_steps: checkpoint default
control_mode: relative
eval_batch_size: 1
max_parallel_tasks: 1
```

Do not silently replace the policy checkpoint or dataset.

The dataset is not used to train anything in this project. It is recorded because it defines the LIBERO preprocessing, normalization, camera conventions, and policy-compatible data configuration.

Before running experiments, save:

```text
LeRobot git commit
checkpoint revision SHA
dataset revision SHA
Python version
PyTorch version
CUDA version
NVIDIA driver
GPU model
MuJoCo version
Robosuite version
LIBERO package version
installed Python packages
```

Write these to:

```text
async_vla_benchmark/outputs/environment.json
```

# 3. Installation

Use a Linux environment with CUDA.

Install LeRobot with π0.5 and LIBERO dependencies:

```bash
git clone https://github.com/huggingface/lerobot.git
cd lerobot
git checkout -b week1-pi05-async-benchmark

pip install -e ".[pi,libero]"
export MUJOCO_GL=egl
```

Do not edit LeRobot core files unless absolutely necessary. Prefer a self-contained package under:

```text
async_vla_benchmark/
```

# 4. Project structure

Create:

```text
async_vla_benchmark/
├── README.md
├── configs/
│   └── days1_3.yaml
├── benchmark/
│   ├── __init__.py
│   ├── environment.py
│   ├── policy.py
│   ├── latency.py
│   ├── queues.py
│   ├── execution.py
│   ├── rtc.py
│   ├── logging.py
│   └── metrics.py
├── scripts/
│   ├── inspect_setup.py
│   ├── select_tasks.py
│   ├── profile_latency.py
│   ├── run_benchmark.py
│   ├── validate_results.py
│   └── make_figures.py
├── tests/
│   ├── test_latency_steps.py
│   ├── test_action_age.py
│   ├── test_async_queue.py
│   ├── test_horizon.py
│   └── test_reproducibility.py
└── outputs/
    ├── requests/
    ├── actions/
    ├── episodes/
    ├── summaries/
    ├── figures/
    └── videos/
```

Document any required changes to LeRobot in:

```text
async_vla_benchmark/UPSTREAM_CHANGES.md
```

# 5. Task selection

Start with these task candidates:

```yaml
task_candidates:
  - name: spatial
    suite: libero_spatial
    task_ids: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

  - name: goal
    suite: libero_goal
    task_ids: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

  - name: long
    suite: libero_10
    task_ids: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
```

For each suite:

1. Start with task ID 0.
2. Run five `ideal_sync` pilot episodes.
3. Accept the task if at least four of five episodes succeed.
4. Otherwise test the next task ID.
5. Select the first task achieving at least 4/5 success.
6. Stop after task ID 9.
7. Do not use a task with poor ideal execution performance.

Write all attempted tasks to:

```text
outputs/summaries/task_selection.csv
```

Include:

```text
suite
task_id
task_name
language_instruction
seed
success
episode_steps
selected
```

Use the three selected tasks for all subsequent experiments.

# 6. Control frequency and logical time

Do not assume a fixed control frequency without inspecting the environment.

Read the environment control or render frequency from the current LeRobot/LIBERO environment metadata.

Set:

```python
control_frequency_hz = resolved_environment_frequency
control_period_seconds = 1.0 / control_frequency_hz
logical_time_seconds = control_step * control_period_seconds
```

Print and record the resolved frequency.

If the environment does not expose a reliable frequency, fail with an actionable error rather than silently choosing one.

# 7. Native latency measurement

Before benchmarking, perform:

```text
10 warm-up policy calls
100 measured policy calls
```

Use observations sampled from actual LIBERO rollouts rather than repeating one synthetic observation.

For each request, record:

```text
observation_capture_time
preprocessing_start_time
preprocessing_end_time
inference_start_time
inference_end_time
postprocessing_end_time
request_complete_time
```

Use `time.perf_counter_ns()` for wall-clock timing.

For CUDA timing:

1. Call `torch.cuda.synchronize()` before the measured inference.
2. Use CUDA events where practical.
3. Synchronize after the inference.
4. Record both GPU event time and complete request wall-clock time.

Calculate:

```text
preprocessing_latency_ms
model_latency_ms
postprocessing_latency_ms
request_latency_ms
```

Report:

```text
mean
standard deviation
minimum
maximum
p50
p90
p95
p99
```

Save:

```text
outputs/summaries/native_latency.csv
outputs/summaries/native_latency.json
outputs/figures/native_latency_histogram.png
```

# 8. Latency profiles

Implement:

```yaml
latency_profiles:
  ideal:
    use_measured_native_latency: false
    added_latency_ms: 0

  native:
    use_measured_native_latency: true
    added_latency_ms: 0

  native_plus_300:
    use_measured_native_latency: true
    added_latency_ms: 300

  native_plus_700:
    use_measured_native_latency: true
    added_latency_ms: 700
```

For every policy request except `ideal`, calculate:

```python
total_logical_latency_ms = measured_request_latency_ms + added_latency_ms

delay_steps = math.ceil(
    total_logical_latency_ms
    / (control_period_seconds * 1000.0)
)
```

For `ideal`:

```python
total_logical_latency_ms = 0.0
delay_steps = 0
```

Still record the actual wall-clock model runtime under `ideal`; only the simulated logical availability delay is zero.

Do not use `round()`. Use `ceil()` because a response arriving after a control deadline cannot be used for that earlier control step.

# 9. Discrete-event latency simulation

Do not insert latency using `time.sleep()`.

The simulator does not need to run in real time.

For each policy request:

1. Capture observation (o_t) at logical control step (t).
2. Run the policy and measure actual request latency.
3. Convert the request latency plus injected delay into `delay_steps`.
4. Treat the generated chunk as unavailable for exactly `delay_steps`.
5. Advance the environment during those steps according to the execution strategy.
6. Make the new chunk available only after those steps have elapsed.

The policy output must remain associated with the observation captured before the elapsed steps.

Allow only one outstanding request.

# 10. Action provenance

Assign every observation:

```text
observation_id
observation_control_step
observation_logical_time
```

Assign every generated chunk:

```text
chunk_id
source_observation_id
request_step
request_logical_time
response_available_step
measured_request_latency_ms
added_latency_ms
delay_steps
```

Assign every executed action:

```text
episode_id
control_step
logical_time_seconds
strategy
latency_profile
fixed_horizon
chunk_id
chunk_action_index
source_observation_id
source_observation_step
action_age_steps
action_age_ms
queue_depth_before
queue_depth_after
is_hold_action
is_queue_underrun
action_vector
```

Calculate:

```python
action_age_steps = (
    execution_control_step - source_observation_control_step
)

action_age_ms = (
    action_age_steps * control_period_seconds * 1000.0
)
```

Do not use inference completion time as action age.

# 11. Hold action

For blocking execution and queue underruns, use a zero-delta end-effector action while preserving the most recent gripper command.

For a seven-dimensional relative action:

```python
hold_action = np.array(
    [
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        last_gripper_command,
    ],
    dtype=np.float32,
)
```

Pass the hold action through the same clipping and environment action-processing logic as model-generated actions.

# 12. Baseline A: ideal synchronous execution

Strategy name:

```text
ideal_sync
```

Semantics:

1. Capture the latest observation.
2. Generate a chunk.
3. Set logical `delay_steps=0`.
4. Execute exactly `fixed_horizon` actions from the chunk.
5. Capture a new observation.
6. Repeat.

Default:

```yaml
fixed_horizon: 10
```

This is the zero-logical-latency upper bound. Actual model runtime must still be measured and logged.

# 13. Baseline B: blocking synchronous execution

Strategy name:

```text
blocking_sync
```

Semantics:

1. Capture the latest observation.
2. Generate a chunk.
3. Calculate request-specific `delay_steps`.
4. Execute hold actions for all `delay_steps`.
5. Execute exactly `fixed_horizon` actions from the returned chunk.
6. Capture a new observation.
7. Repeat.

Default:

```yaml
fixed_horizon: 10
```

Run this baseline under:

```text
native
native_plus_300
native_plus_700
```

# 14. Baseline C: naive asynchronous queue

Strategy name:

```text
naive_async
```

Maintain an action queue.

Default configuration:

```yaml
fixed_horizon: 10
request_threshold_actions: 5
merge_rule: replace
maximum_outstanding_requests: 1
```

Semantics:

1. Begin with an initial chunk generated under ideal startup conditions, or record startup separately.
2. Execute one queued action per control step.
3. Start a new request when queue length becomes less than or equal to five actions.
4. Capture the request observation at the trigger step.
5. During `delay_steps`, continue consuming the old queue.
6. If the queue empties before the response becomes available, execute hold actions and record queue underruns.
7. When the new chunk becomes available, discard all unexecuted actions from the old queue.
8. Insert the first `fixed_horizon` actions from the new chunk.
9. Continue execution.

Do not average old and new chunks in this baseline.

Record:

```text
discarded_old_actions
queue_underrun_steps
hold_steps
queue_depth
```

# 15. Baseline D: RTC

Strategy name:

```text
rtc
```

Use LeRobot’s current RTC implementation. Do not reimplement RTC guidance.

Initial configuration:

```yaml
rtc:
  enabled: true
  execution_horizon: 10
  max_guidance_weight: 10.0
  prefix_attention_schedule: EXP
  request_threshold_actions: 5
```

For every request:

1. Capture the current observation.
2. Obtain the current unexecuted remainder of the previous chunk.
3. Calculate request-specific `delay_steps`.
4. Call the RTC-capable `predict_action_chunk` path with:

   * `inference_delay=delay_steps`;
   * `prev_chunk_left_over=current unexecuted actions`.
5. Continue executing the old queue while the request is logically pending.
6. Merge the RTC result using the current LeRobot RTC queue behavior.
7. Record the number of overlapping and guided actions.

The runtime `inference_delay` must use the current request’s measured latency. Do not use a global average.

If the current LeRobot RTC API differs from its documentation:

1. Inspect the installed source.
2. adapt the wrapper to the actual API;
3. preserve request-specific delay semantics;
4. document the difference;
5. add a regression test.

# 16. Fixed execution-horizon sweep

Run the fixed-horizon sweep for:

```text
naive_async
rtc
```

Use:

```yaml
execution_horizons: [2, 5, 10]
```

Interpretation:

* `2`: frequent replanning and high freshness;
* `5`: intermediate execution;
* `10`: published/default π0.5 action-execution setting.

For `naive_async`, `fixed_horizon` is the number of actions inserted from each returned chunk.

Set the request threshold to:

```python
request_threshold_actions = math.ceil(fixed_horizon / 2)
```

Therefore:

```text
horizon 2  -> threshold 1
horizon 5  -> threshold 3
horizon 10 -> threshold 5
```

For RTC:

```text
rtc.execution_horizon = fixed_horizon
request_threshold_actions = ceil(fixed_horizon / 2)
```

Use the same horizon and threshold for paired `naive_async` and RTC runs.

Run the horizon sweep under:

```text
native
native_plus_700
```

Do not tune the horizon separately for each task.

# 17. Episode metrics

For every episode, calculate:

```text
success
environment_steps
logical_completion_time_seconds
wall_clock_runtime_seconds
number_of_policy_requests
total_model_inference_ms
mean_request_latency_ms
p95_request_latency_ms
mean_action_age_ms
p95_action_age_ms
maximum_action_age_ms
mean_queue_depth
minimum_queue_depth
queue_underrun_steps
hold_action_steps
discarded_old_actions
mean_action_delta_l2
mean_action_acceleration_l2
mean_action_jerk_l2
```

For action continuity, use only the robot-motion dimensions unless the gripper dimension is intentionally included and reported separately.

# 18. Experiment matrix

Use five paired seeds:

```yaml
seeds: [0, 1, 2, 3, 4]
```

## Core baseline experiment

For each of the three selected tasks:

```text
ideal_sync:
  latency profile: ideal
  fixed horizon: 10

blocking_sync:
  latency profiles:
    - native
    - native_plus_300
    - native_plus_700
  fixed horizon: 10

naive_async:
  latency profiles:
    - native
    - native_plus_300
    - native_plus_700
  fixed horizon: 10

rtc:
  latency profiles:
    - native
    - native_plus_300
    - native_plus_700
  fixed horizon: 10
```

Run five episodes per condition.

Total:

```text
3 tasks
× [1 ideal condition + 9 delayed strategy conditions]
× 5 seeds
= 150 episodes
```

## Horizon sweep

For each selected task:

```text
strategies:
  - naive_async
  - rtc

latency profiles:
  - native
  - native_plus_700

fixed horizons:
  - 2
  - 5
  - 10

seeds:
  - 0
  - 1
  - 2
```

Use three seeds for the initial horizon sweep.

The `horizon=10` conditions may reuse validated runs from the core experiment.

Maximum new episodes:

```text
3 tasks
× 2 strategies
× 2 latency profiles
× 3 horizons
× 3 seeds
= 108 episodes
```

With horizon-10 reuse, fewer new runs are required.

# 19. Required tests

Implement:

## Latency conversion

At a 100 ms control period:

```text
0 ms -> 0 steps
1 ms -> 1 step
100 ms -> 1 step
101 ms -> 2 steps
300 ms -> 3 steps
700 ms -> 7 steps
```

The test must use the general conversion function rather than a hard-coded 100 ms implementation.

## Action age

For a chunk generated from an observation at step 10:

```text
action executed at step 13 -> age 3 steps
action executed at step 14 -> age 4 steps
action executed at step 15 -> age 5 steps
```

## Naive queue

Verify:

```text
request begins at the correct threshold
old actions execute while response is pending
old remainder is discarded on replacement
queue underrun produces hold actions
only one request may be active
```

## Horizon behavior

Verify that:

```text
horizon 2 inserts exactly 2 actions
horizon 5 inserts exactly 5 actions
horizon 10 inserts exactly 10 actions
request threshold equals ceil(horizon / 2)
```

## RTC

Verify that RTC receives:

```text
request-specific delay_steps
current previous-chunk remainder
configured execution horizon
```

## Reproducibility

Verify that the same task, initialization index, and seed produce the same initial simulator state across strategies.

# 20. Required outputs

Write one policy-request record per row to:

```text
outputs/requests/<episode_id>.parquet
```

Write one executed-action record per row to:

```text
outputs/actions/<episode_id>.parquet
```

Write episode summaries to:

```text
outputs/episodes/<episode_id>.json
outputs/summaries/episodes.csv
outputs/summaries/requests.csv
outputs/summaries/horizon_sweep.csv
```

Create:

```text
outputs/figures/native_latency_distribution.png
outputs/figures/success_vs_delay.png
outputs/figures/action_age_vs_delay.png
outputs/figures/queue_underruns_vs_delay.png
outputs/figures/completion_time_vs_delay.png
outputs/figures/action_jerk_vs_delay.png
outputs/figures/horizon_success_tradeoff.png
outputs/figures/horizon_action_age_tradeoff.png
```

Use bootstrap 95% confidence intervals over episodes.

Clearly label results based on three or five episodes as preliminary.

# 21. Validation

Make `validate_results.py` fail when:

```text
timestamps are nonmonotonic
action age is negative
an action references a missing chunk
a chunk references a missing observation
queue depth is negative
more than one request is outstanding
delay-step conversion is incorrect
RTC receives a global average delay
an episode is missing its terminal result
a horizon run executes more than its configured horizon
CUDA timing is measured without synchronization
```

Do not generate aggregate figures until validation passes.

# 22. Commands

Provide working commands resembling:

```bash
python async_vla_benchmark/scripts/inspect_setup.py

python async_vla_benchmark/scripts/select_tasks.py \
  --config async_vla_benchmark/configs/days1_3.yaml

python async_vla_benchmark/scripts/profile_latency.py \
  --config async_vla_benchmark/configs/days1_3.yaml \
  --warmup-requests 10 \
  --measured-requests 100

python async_vla_benchmark/scripts/run_benchmark.py \
  --config async_vla_benchmark/configs/days1_3.yaml \
  --experiment core

python async_vla_benchmark/scripts/run_benchmark.py \
  --config async_vla_benchmark/configs/days1_3.yaml \
  --experiment horizon_sweep

python async_vla_benchmark/scripts/validate_results.py \
  --output-dir async_vla_benchmark/outputs

python async_vla_benchmark/scripts/make_figures.py \
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
--fixed-horizon
--overwrite
```

`--dry-run` must print every planned episode without loading the model.

`--resume` must skip only completed and validated episodes.

# 23. Day-by-day deliverables

## Day 1

Complete:

```text
environment setup
checkpoint loading
LIBERO task selection
ideal synchronous evaluation
native latency profiling
metadata capture
```

Required outputs:

```text
environment.json
task_selection.csv
native_latency.csv
native_latency_distribution.png
```

## Day 2

Complete:

```text
blocking synchronous execution
naive asynchronous queue
request-specific delay conversion
action provenance
action-age logging
queue tests
core runs for at least one task
```

Required preliminary plots:

```text
success vs delay
action age vs delay
queue underruns vs delay
```

## Day 3

Complete:

```text
RTC integration
RTC regression test
fixed-horizon sweep
all selected-task core runs
result validation
summary figures
```

# 24. Final three-day report

Create:

```text
outputs/summaries/days1_3_report.md
```

Answer:

1. What are the native p50, p95, and p99 request latencies?
2. How many control steps does native inference occupy?
3. How much higher is action age than raw inference latency?
4. Does asynchronous buffering prevent blocking pauses?
5. Does naive buffering increase stale-action execution?
6. Does RTC improve task success over naive asynchronous replacement?
7. Does RTC primarily improve continuity, freshness, or both?
8. How frequently does each method experience queue underruns?
9. Which fixed execution horizon performs best for each task?
10. Is one fixed horizon consistently optimal across tasks and latency profiles?
11. Are the differences large enough to justify adding VLASH and FASTER?
12. What implementation or reproducibility problems remain?

# 25. Go/no-go criteria

Recommend continuing when at least three conditions hold:

```text
success degradation differs across latency profiles
naive async and RTC have meaningfully different outcomes
action age differs substantially from raw request latency
queue underruns occur under realistic or stress latency
fixed horizon changes the success–latency trade-off
no single horizon is uniformly optimal
RTC improves continuity but leaves measurable freshness limitations
```

Recommend stopping or reframing when:

```text
ideal baseline success is poor
all execution strategies produce nearly identical results
native latency is negligible relative to the execution horizon
action age is nearly identical for naive async and RTC
the horizon sweep has no measurable effect
RTC cannot be reproduced or validated in the current stack
```

# 26. Completion requirements

Do not report completion until:

```text
the exact checkpoint has loaded on CUDA
three viable tasks have been selected or failures documented
100 native requests have been profiled
core baseline logs have passed validation
RTC has been verified with request-specific delays
the horizon sweep has completed or failures are documented
all required summary files and figures have been generated
```

At completion, report:

```text
files created and modified
exact repository and model revisions
commands used
selected task IDs
number of completed episodes
failed or skipped episodes
native latency statistics
validation status
preliminary findings
paths to summaries and figures
remaining limitations
```
