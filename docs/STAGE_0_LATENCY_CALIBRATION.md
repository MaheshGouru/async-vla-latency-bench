# Stage 0 — ID-Only Latency Calibration

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

and both exploratory seeds.

Therefore the Stage 1 OOD factorial is:

```text
3 task groups
× 7 perturbation families
× 2 latency levels
× 2 execution methods
× 2 seeds
= 168 OOD episodes
```

The purpose of Stage 0 is only to determine what `d*` should be.

Stage 1 then asks:

> **Which kinds of distribution shift reduce a VLA policy’s tolerance to inference delay, and under which behavioral demands?**

---

## 2. Policy and execution configuration

Use:

```text
policy = lerobot/pi05_libero_finetuned
policy.n_action_steps = 10
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

## 4. Latencies to test

Test exactly eight **added-delay** settings:

| `added_delay_ms` | Display label | Meaning |
|---:|---|---|
| `0` | **Native** | No artificial delay; measured model/runtime latency remains present |
| `100` | **Native + 100 ms** | Native request latency plus 100 ms |
| `200` | **Native + 200 ms** | Native request latency plus 200 ms |
| `300` | **Native + 300 ms** | Native request latency plus 300 ms |
| `400` | **Native + 400 ms** | Native request latency plus 400 ms |
| `500` | **Native + 500 ms** | Native request latency plus 500 ms |
| `600` | **Native + 600 ms** | Native request latency plus 600 ms |
| `700` | **Native + 700 ms** | Native request latency plus 700 ms |

Important:

- These values are **added artificial delay**, not total request latency.
- Log the actual measured total request latency for every request.
- Also convert total latency to effective logical delay in control steps.
- Include `+700 ms` in calibration so the full degradation curve is observed, but do not automatically choose it if it is already saturated.
- Do not use different delays for different task groups or execution methods.

---

## 5. Seeds and total budget

Use the same exploratory seeds as Stage 1:

```text
seed = 0
seed = 1
```

Calibration budget:

```text
3 tasks
× 2 methods
× 8 added-delay settings
× 2 seeds
= 96 episodes
```

There are **48 unique task × method × delay condition blocks**, each with 2 seeds.

The `Native` episodes and the episodes at the eventually selected `d*` become the Stage 1 shared ID controls.

Therefore:

```text
Stage 0 unique episodes = 96
Stage 1 OOD episodes    = 168
--------------------------------
Total unique episodes   = 264
```

Do not rerun the 24 selected ID low/high episodes unless a run is invalid.

---

## 6. Complete calibration experiment table

### 6.1 Condition-level matrix — 48 conditions

| # | Task-demand group | Suite:task_id | Method | Added delay | Seeds | Episodes |
|---:|---|---|---|---|---|---:|
| 1 | Single-stage transport | `libero_spatial:2` | Naive async | Native | `0, 1` | 2 |
| 2 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 100 ms | `0, 1` | 2 |
| 3 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 200 ms | `0, 1` | 2 |
| 4 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 300 ms | `0, 1` | 2 |
| 5 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 400 ms | `0, 1` | 2 |
| 6 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 500 ms | `0, 1` | 2 |
| 7 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 600 ms | `0, 1` | 2 |
| 8 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 700 ms | `0, 1` | 2 |
| 9 | Single-stage transport | `libero_spatial:2` | RTC | Native | `0, 1` | 2 |
| 10 | Single-stage transport | `libero_spatial:2` | RTC | Native + 100 ms | `0, 1` | 2 |
| 11 | Single-stage transport | `libero_spatial:2` | RTC | Native + 200 ms | `0, 1` | 2 |
| 12 | Single-stage transport | `libero_spatial:2` | RTC | Native + 300 ms | `0, 1` | 2 |
| 13 | Single-stage transport | `libero_spatial:2` | RTC | Native + 400 ms | `0, 1` | 2 |
| 14 | Single-stage transport | `libero_spatial:2` | RTC | Native + 500 ms | `0, 1` | 2 |
| 15 | Single-stage transport | `libero_spatial:2` | RTC | Native + 600 ms | `0, 1` | 2 |
| 16 | Single-stage transport | `libero_spatial:2` | RTC | Native + 700 ms | `0, 1` | 2 |
| 17 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native | `0, 1` | 2 |
| 18 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 100 ms | `0, 1` | 2 |
| 19 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 200 ms | `0, 1` | 2 |
| 20 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 300 ms | `0, 1` | 2 |
| 21 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 400 ms | `0, 1` | 2 |
| 22 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 500 ms | `0, 1` | 2 |
| 23 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 600 ms | `0, 1` | 2 |
| 24 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 700 ms | `0, 1` | 2 |
| 25 | Articulated/contact-rich | `libero_goal:0` | RTC | Native | `0, 1` | 2 |
| 26 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 100 ms | `0, 1` | 2 |
| 27 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 200 ms | `0, 1` | 2 |
| 28 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 300 ms | `0, 1` | 2 |
| 29 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 400 ms | `0, 1` | 2 |
| 30 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 500 ms | `0, 1` | 2 |
| 31 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 600 ms | `0, 1` | 2 |
| 32 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 700 ms | `0, 1` | 2 |
| 33 | Multi-stage/sequential | `libero_10:2` | Naive async | Native | `0, 1` | 2 |
| 34 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 100 ms | `0, 1` | 2 |
| 35 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 200 ms | `0, 1` | 2 |
| 36 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 300 ms | `0, 1` | 2 |
| 37 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 400 ms | `0, 1` | 2 |
| 38 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 500 ms | `0, 1` | 2 |
| 39 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 600 ms | `0, 1` | 2 |
| 40 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 700 ms | `0, 1` | 2 |
| 41 | Multi-stage/sequential | `libero_10:2` | RTC | Native | `0, 1` | 2 |
| 42 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 100 ms | `0, 1` | 2 |
| 43 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 200 ms | `0, 1` | 2 |
| 44 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 300 ms | `0, 1` | 2 |
| 45 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 400 ms | `0, 1` | 2 |
| 46 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 500 ms | `0, 1` | 2 |
| 47 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 600 ms | `0, 1` | 2 |
| 48 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 700 ms | `0, 1` | 2 |

### 6.2 Episode-level manifest — all 96 episodes

| Exp. | Task-demand group | Suite:task_id | Method | Added delay (ms) | Delay label | Seed |
|---:|---|---|---|---:|---|---:|
| C001 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 0 |
| C002 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 1 |
| C003 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 0 |
| C004 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 1 |
| C005 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 0 |
| C006 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 1 |
| C007 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 0 |
| C008 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 1 |
| C009 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 0 |
| C010 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 1 |
| C011 | Single-stage transport | `libero_spatial:2` | Naive async | 500 | Native + 500 ms | 0 |
| C012 | Single-stage transport | `libero_spatial:2` | Naive async | 500 | Native + 500 ms | 1 |
| C013 | Single-stage transport | `libero_spatial:2` | Naive async | 600 | Native + 600 ms | 0 |
| C014 | Single-stage transport | `libero_spatial:2` | Naive async | 600 | Native + 600 ms | 1 |
| C015 | Single-stage transport | `libero_spatial:2` | Naive async | 700 | Native + 700 ms | 0 |
| C016 | Single-stage transport | `libero_spatial:2` | Naive async | 700 | Native + 700 ms | 1 |
| C017 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 0 |
| C018 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 1 |
| C019 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 0 |
| C020 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 1 |
| C021 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 0 |
| C022 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 1 |
| C023 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 0 |
| C024 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 1 |
| C025 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 0 |
| C026 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 1 |
| C027 | Single-stage transport | `libero_spatial:2` | RTC | 500 | Native + 500 ms | 0 |
| C028 | Single-stage transport | `libero_spatial:2` | RTC | 500 | Native + 500 ms | 1 |
| C029 | Single-stage transport | `libero_spatial:2` | RTC | 600 | Native + 600 ms | 0 |
| C030 | Single-stage transport | `libero_spatial:2` | RTC | 600 | Native + 600 ms | 1 |
| C031 | Single-stage transport | `libero_spatial:2` | RTC | 700 | Native + 700 ms | 0 |
| C032 | Single-stage transport | `libero_spatial:2` | RTC | 700 | Native + 700 ms | 1 |
| C033 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 0 |
| C034 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 1 |
| C035 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 0 |
| C036 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 1 |
| C037 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 0 |
| C038 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 1 |
| C039 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 0 |
| C040 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 1 |
| C041 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 0 |
| C042 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 1 |
| C043 | Articulated/contact-rich | `libero_goal:0` | Naive async | 500 | Native + 500 ms | 0 |
| C044 | Articulated/contact-rich | `libero_goal:0` | Naive async | 500 | Native + 500 ms | 1 |
| C045 | Articulated/contact-rich | `libero_goal:0` | Naive async | 600 | Native + 600 ms | 0 |
| C046 | Articulated/contact-rich | `libero_goal:0` | Naive async | 600 | Native + 600 ms | 1 |
| C047 | Articulated/contact-rich | `libero_goal:0` | Naive async | 700 | Native + 700 ms | 0 |
| C048 | Articulated/contact-rich | `libero_goal:0` | Naive async | 700 | Native + 700 ms | 1 |
| C049 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 0 |
| C050 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 1 |
| C051 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 0 |
| C052 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 1 |
| C053 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 0 |
| C054 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 1 |
| C055 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 0 |
| C056 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 1 |
| C057 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 0 |
| C058 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 1 |
| C059 | Articulated/contact-rich | `libero_goal:0` | RTC | 500 | Native + 500 ms | 0 |
| C060 | Articulated/contact-rich | `libero_goal:0` | RTC | 500 | Native + 500 ms | 1 |
| C061 | Articulated/contact-rich | `libero_goal:0` | RTC | 600 | Native + 600 ms | 0 |
| C062 | Articulated/contact-rich | `libero_goal:0` | RTC | 600 | Native + 600 ms | 1 |
| C063 | Articulated/contact-rich | `libero_goal:0` | RTC | 700 | Native + 700 ms | 0 |
| C064 | Articulated/contact-rich | `libero_goal:0` | RTC | 700 | Native + 700 ms | 1 |
| C065 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 0 |
| C066 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 1 |
| C067 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 0 |
| C068 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 1 |
| C069 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 0 |
| C070 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 1 |
| C071 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 0 |
| C072 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 1 |
| C073 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 0 |
| C074 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 1 |
| C075 | Multi-stage/sequential | `libero_10:2` | Naive async | 500 | Native + 500 ms | 0 |
| C076 | Multi-stage/sequential | `libero_10:2` | Naive async | 500 | Native + 500 ms | 1 |
| C077 | Multi-stage/sequential | `libero_10:2` | Naive async | 600 | Native + 600 ms | 0 |
| C078 | Multi-stage/sequential | `libero_10:2` | Naive async | 600 | Native + 600 ms | 1 |
| C079 | Multi-stage/sequential | `libero_10:2` | Naive async | 700 | Native + 700 ms | 0 |
| C080 | Multi-stage/sequential | `libero_10:2` | Naive async | 700 | Native + 700 ms | 1 |
| C081 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 0 |
| C082 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 1 |
| C083 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 0 |
| C084 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 1 |
| C085 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 0 |
| C086 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 1 |
| C087 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 0 |
| C088 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 1 |
| C089 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 0 |
| C090 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 1 |
| C091 | Multi-stage/sequential | `libero_10:2` | RTC | 500 | Native + 500 ms | 0 |
| C092 | Multi-stage/sequential | `libero_10:2` | RTC | 500 | Native + 500 ms | 1 |
| C093 | Multi-stage/sequential | `libero_10:2` | RTC | 600 | Native + 600 ms | 0 |
| C094 | Multi-stage/sequential | `libero_10:2` | RTC | 600 | Native + 600 ms | 1 |
| C095 | Multi-stage/sequential | `libero_10:2` | RTC | 700 | Native + 700 ms | 0 |
| C096 | Multi-stage/sequential | `libero_10:2` | RTC | 700 | Native + 700 ms | 1 |

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

compute Native success over the two seeds.

A task × method cell is **viable for delay calibration** if:

```text
Native success >= 1 / 2
```

Cells already at `0 / 2` under Native are retained in all tables but are not allowed to determine the high-delay choice because they are already at floor.

### 8.2 Compute calibration summary

For each candidate:

```text
d ∈ {100, 200, 300, 400, 500, 600, 700} ms
```

using only the viable cells, calculate:

```text
S_native
S_d
delay_drop(d) = S_d - S_native
```

where success is pooled over the same viable task × method cells and both seeds.

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

3. Otherwise choose `700 ms` and flag:

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

| Task-demand group | Method | Native | +100 | +200 | +300 | +400 | +500 | +600 | +700 ms | Viable? |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|

Cells contain:

```text
successes / 2
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
| 500 ms | ... | ... | ... | ... |
| 600 ms | ... | ... | ... | ... |
| 700 ms | ... | ... | ... | ... |

Mark the selected `d*`.

---

### Table C — Execution-method calibration

| Method | Native | +100 | +200 | +300 | +400 | +500 | +600 | +700 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Naive async | ... | ... | ... | ... | ... | ... | ... | ... |
| RTC | ... | ... | ... | ... | ... | ... | ... | ... |

Use this only descriptively. The selected `d*` remains common to both methods.

---

### Table D — Freshness calibration

| Added delay | Method | mean action age | p95 action age | p95 logical delay steps | underruns | discards |
|---:|---|---:|---:|---:|---:|---:|

---

## 10. Plots to generate

### Plot 1 — ID success vs added delay

- x-axis: added delay (`0`, `100`, `200`, `300`, `400`, `500`, `600`, `700 ms`)
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
- Expected episodes: 96
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
- +500 ms pooled success:
- +600 ms pooled success:
- +700 ms pooled success:

## Freshness response
- Native p95 action age:
- +100 ms p95 action age:
- +200 ms p95 action age:
- +300 ms p95 action age:
- +400 ms p95 action age:
- +500 ms p95 action age:
- +600 ms p95 action age:
- +700 ms p95 action age:

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

> “To avoid tuning latency against OOD outcomes, we select the high-delay condition using only standard LIBERO tasks. We evaluate 0, 100, 200, 300, 400, 500, 600, and 700 ms of added delay under both Naive async and RTC, then freeze the smallest delay that produces at least a 20 percentage-point reduction in pooled success on viable ID conditions while retaining at least 25% success.”

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

ADDED DELAYS:
    0 ms
    100 ms
    200 ms
    300 ms
    400 ms
    500 ms
    600 ms
    700 ms

SEEDS:
    0
    1

TOTAL:
    96 episodes

OUTPUT:
    one frozen high delay d*

OOD USED TO SELECT d*:
    no

STAGE 1 USE:
    Native vs Native + d*
    on all 7 LIBERO-Plus perturbation families
```
