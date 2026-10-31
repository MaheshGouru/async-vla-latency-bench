# Stage 0 — ID-Only Latency Calibration

> **Current protocol (D016):** The completed revised calibration uses
> `n_action_steps=25`, seeds `0, 1, 10, 11, 12, 13`, and added delays
> `0, 100, 200, 300, 400 ms` (180 episodes). All matrices, selection rules,
> tables, plots, and reporting instructions below describe this revised design.

## 0. Role in the paper

Yes: this calibration is part of the paper.

It belongs in **Methods / Experimental Setup**, with the full calibration curve optionally placed in the appendix. Its purpose is to choose the Stage 1 high-latency condition **without looking at any OOD results**.

Recommended paper wording:

> “We calibrate the added inference delay using only in-distribution LIBERO tasks. We then freeze a single non-saturating high-delay level and use that same delay for every LIBERO-Plus perturbation, task group, and asynchronous execution method.”

This prevents the high-delay setting from being chosen after seeing which OOD conditions produce the strongest result.

---

## 1. Relationship to Stage 1

**Stage 1 DOES test OOD under latency.**

For every selected LIBERO-Plus OOD variant, Stage 1 runs:

```text
OOD + Native
OOD + Native + d*
```

for both:

```text
Naive async
RTC
```

and all five exploratory seeds.

Therefore the Stage 1 OOD factorial is:

```text
3 task groups
× 7 perturbation families
× 2 latency levels
× 2 execution methods
× 5 seeds
= 420 OOD episodes
```

The purpose of Stage 0 is only to determine what `d*` should be.

Stage 1 then asks:

> **Which kinds of distribution shift reduce a VLA policy’s tolerance to inference delay, and under which behavioral demands?**

---

## 2. Policy and execution configuration

Use:

```text
policy = lerobot/pi05_libero_finetuned
policy.n_action_steps = 25
```

Execution methods:

```text
naive_async
rtc
```

Do not use LIBERO-Plus/OOD environments during Stage 0.

---

## 3. Exact ID tasks

Use the same three standard-LIBERO base tasks that Stage 1 will perturb.

| Task-demand group | Suite | Zero-based task ID | Exact task |
|---|---|---:|---|
| **Single-stage transport** | `libero_spatial` | **2** | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate` |
| **Articulated/contact-rich** | `libero_goal` | **0** | `open_the_middle_drawer_of_the_cabinet` |
| **Multi-stage/sequential** | `libero_10` | **2** | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it` |

Before execution:

```python
assert task_suite.get_task(task_id).name == EXPECTED_TASK_NAME
```

---

## 4. Added-delay grid

The completed calibration uses exactly five **added-delay** settings:

| `added_delay_ms` | Display label | Meaning |
|---:|---|---|
| `0` | **Native** | No artificial delay; measured model/runtime latency remains present |
| `100` | **Native + 100 ms** | Native request latency plus 100 ms |
| `200` | **Native + 200 ms** | Native request latency plus 200 ms |
| `300` | **Native + 300 ms** | Native request latency plus 300 ms |
| `400` | **Native + 400 ms** | Native request latency plus 400 ms |

Important:

- These values are added artificial delay, not total request latency.
- Log actual measured total request latency for every request.
- Convert total latency to effective logical delay in control steps.
- No `500–700 ms` extension or rerun is required under D016.
- Do not use different delays for different task groups or execution methods.

---

## 5. Seeds and total budget

Use the six fixed Stage 0 seeds:

```text
0, 1, 10, 11, 12, 13
```

Calibration budget:

```text
3 tasks
× 2 methods
× 5 added-delay settings
× 6 seeds
= 180 episodes
```

There are 30 unique task × method × delay condition blocks, each with six
seeds.

The Native and selected-`d*` episodes for seeds `0` and `1` may provide 24
of the Stage 1 shared ID controls when every configuration and provenance field
matches. Stage 1 independently uses seeds `0–4` and therefore runs the 36
missing ID controls for seeds `2`, `3`, and `4`.

Therefore:

```text
Stage 0 unique episodes        = 180
Stage 1 OOD episodes           = 420
Stage 1 additional ID controls = 36
--------------------------------------
Total unique episodes          = 636
```

---

## 6. Complete calibration experiment matrix

### 6.1 Condition-level matrix — 30 conditions

Materialize the Cartesian product:

```text
tasks   = [libero_spatial:2, libero_goal:0, libero_10:2]
methods = [naive_async, rtc]
delays  = [0, 100, 200, 300, 400]
seeds   = [0, 1, 10, 11, 12, 13]
```

Each task × method × delay block contains six episodes. The generated manifest
must satisfy:

```python
assert len(condition_rows) == 30
assert len(episode_rows) == 180
assert sorted({row["seed"] for row in episode_rows}) == [0, 1, 10, 11, 12, 13]
assert sorted({row["added_delay_ms"] for row in episode_rows}) == [0, 100, 200, 300, 400]
```

### 6.2 Episode-level manifest — all 180 episodes

Assign deterministic IDs after expanding the 30 condition rows over all six
seeds. Do not omit failed cells from the planned manifest. Save the materialized
manifest with the run artifacts so the 180 planned rows can be compared with the
180 completed summaries.

---

## 7. Required calibration logging

Create:

```text
latency_calibration_episode_results.csv
```

One row per episode.

Required columns:

```text
run_id
task_key
task_group
suite
task_id
task_name
execution_method
added_delay_ms
seed

success
episode_steps
completion_fraction

request_latency_mean_ms
request_latency_p50_ms
request_latency_p95_ms

action_age_mean_ms
action_age_p50_ms
action_age_p95_ms
action_age_max_ms

logical_delay_steps_mean
logical_delay_steps_p95

queue_occupancy_mean
queue_occupancy_p95
underrun_count
hold_count
discard_count
num_policy_requests

action_delta_mean
action_accel_mean
action_jerk_mean

wall_clock_episode_s
gpu_id
status
invalid_reason
```

Keep `hold_count` and `underrun_count` separate.

---

## 8. How to choose `d*`

### 8.1 First define viable ID cells

For each of the six:

```text
3 tasks × 2 methods
```

compute Native success over all six seeds.

A task × method cell is **viable for delay calibration** if:

```text
Native success >= 3 / 6
```

Cells below `3 / 6` under Native are retained in all tables but are not allowed to determine the high-delay choice because they are already at floor.

### 8.2 Compute calibration summary

For each candidate:

```text
d ∈ {100, 200, 300, 400} ms
```

using only the viable cells, calculate:

```text
S_native
S_d
delay_drop(d) = S_d - S_native
```

where success is pooled over the same viable task × method cells and all six seeds.

### 8.3 Frozen selection rule

Choose the **smallest** candidate `d` satisfying both:

```text
S_native - S_d >= 0.20
```

and:

```text
S_d >= 0.25
```

Interpretation:

- at least a **20 percentage-point success drop**, so the latency manipulation has a visible effect;
- at least **25% success remains**, so the condition is not broadly saturated.

Also require:

```text
at least 2 viable task × method cells
retain >= 1 successful episode at d
```

This prevents a pooled number from hiding complete collapse everywhere except one cell.

### 8.4 Fallback rules

Apply these in order if no candidate satisfies the primary rule:

1. If at least one candidate has `S_d >= 0.25`, choose the candidate with the **largest success drop**; break ties toward the smaller delay.
2. Otherwise, if at least one candidate produces a drop of at least 10 percentage points, choose the **smallest** such delay and flag:

```text
CALIBRATION_SATURATED = true
```

3. Otherwise choose `400 ms` and flag:

```text
CALIBRATION_WEAK = true
```

The flags describe the calibration result; they are not reasons to retune using OOD data.

Do not change the rule after inspecting OOD results.

### 8.5 Freeze the result

Write:

```text
selected_high_delay.json
```

with:

```json
{
  "low_added_delay_ms": 0,
  "high_added_delay_ms": "<d*>",
  "selection_used_ood_results": false,
  "calibration_saturated": false,
  "calibration_weak": false
}
```

Then Stage 1 reads this file rather than hard-coding its own delay.

---

## 9. Tables to generate

### Table A — Per-task calibration

| Task-demand group | Method | Native | +100 | +200 | +300 | +400 | Viable? |
|---|---|---:|---:|---:|---:|---:|---|

Cells contain:

```text
successes / 6
```

---

### Table B — Pooled calibration curve

| Added delay | Success on viable ID cells | Drop from Native | Mean request latency | p95 action age |
|---:|---:|---:|---:|---:|
| 0 ms | ... | 0 | ... | ... |
| 100 ms | ... | ... | ... | ... |
| 200 ms | ... | ... | ... | ... |
| 300 ms | ... | ... | ... | ... |
| 400 ms | ... | ... | ... | ... |

Mark the selected `d*`.

---

### Table C — Execution-method calibration

| Method | Native | +100 | +200 | +300 | +400 |
|---|---:|---:|---:|---:|---:|
| Naive async | ... | ... | ... | ... | ... |
| RTC | ... | ... | ... | ... | ... |

Use this only descriptively. The selected `d*` remains common to both methods.

---

### Table D — Freshness calibration

| Added delay | Method | mean action age | p95 action age | p95 logical delay steps | underruns | discards |
|---:|---|---:|---:|---:|---:|---:|

---

## 10. Plots to generate

### Plot 1 — ID success vs added delay

- x-axis: added delay (`0`, `100`, `200`, `300`, `400 ms`)
- y-axis: success rate
- line: execution method
- facet: task-demand group

This is the primary calibration plot.

### Plot 2 — Pooled calibration curve

- x-axis: added delay
- y-axis: pooled success on viable ID cells
- mark selected `d*`

### Plot 3 — Action age vs added delay

- x-axis: added delay
- y-axis: p95 action age
- line: execution method
- facet: task-demand group

This checks that the artificial delay actually produces the intended temporal-staleness change.

### Plot 4 — Logical delay steps vs added delay

- x-axis: added delay
- y-axis: mean/p95 logical delay steps
- line: execution method

This makes the latency manipulation interpretable relative to the control horizon.

---

## 11. Calibration observation template

Generate:

```text
LATENCY_CALIBRATION_OBSERVATIONS.md
```

with:

```markdown
# Latency Calibration Observations

## Coverage
- Expected episodes: 180
- Completed:
- Invalid:
- Rerun:

## Native ID viability
### Single-stage transport
- Naive async:
- RTC:

### Articulated/contact-rich
- Naive async:
- RTC:

### Multi-stage/sequential
- Naive async:
- RTC:

## Delay-response curve
- Native pooled success:
- +100 ms pooled success:
- +200 ms pooled success:
- +300 ms pooled success:
- +400 ms pooled success:

## Freshness response
- Native p95 action age:
- +100 ms p95 action age:
- +200 ms p95 action age:
- +300 ms p95 action age:
- +400 ms p95 action age:

## Selected high delay
- d*:
- Selection criterion satisfied:
- Calibration saturated:
- Calibration weak:
- Exact reason for selection:

## Data-quality warnings
- Latency drift:
- Floor cells:
- Queue anomalies:
- Invalid episodes:
```

---

## 12. Paper verbiage

### Methods

Use:

> “To avoid tuning latency against OOD outcomes, we select the high-delay condition using only standard LIBERO tasks. We evaluate 0, 100, 200, 300, and 400 ms of added delay under both Naive async and RTC, then freeze the smallest delay that produces at least a 20 percentage-point reduction in pooled success on viable ID conditions while retaining at least 25% success.”

### Stage 1 transition

Use:

> “The selected delay is then held fixed across all LIBERO-Plus perturbation families, task-demand groups, and execution methods.”

### Do not write

```text
We chose the latency that produced the strongest OOD effect.
```

or:

```text
We tuned the delay separately for each perturbation.
```

---

## 13. Required artifacts

```text
latency_calibration_manifest.csv
latency_calibration_episode_results.csv
latency_calibration_table_per_task.csv
latency_calibration_table_pooled.csv
latency_calibration_table_method.csv
latency_calibration_table_freshness.csv

latency_calibration_success_by_task.png
latency_calibration_pooled_curve.png
latency_calibration_action_age.png
latency_calibration_logical_steps.png

selected_high_delay.json
LATENCY_CALIBRATION_OBSERVATIONS.md
```

---

## 14. Frozen Stage 0 summary

```text
DATA:
    Standard LIBERO only (ID)

TASK GROUPS:
    Single-stage transport
    Articulated/contact-rich
    Multi-stage/sequential

METHODS:
    Naive async
    RTC

N_ACTION_STEPS:
    25

ADDED DELAYS:
    0 ms
    100 ms
    200 ms
    300 ms
    400 ms

SEEDS:
    0
    1
    10
    11
    12
    13

TOTAL:
    180 episodes

OUTPUT:
    one frozen high delay d*

OOD USED TO SELECT d*:
    no

STAGE 1 USE:
    Native vs Native + d*
    on all 7 LIBERO-Plus perturbation families
```
