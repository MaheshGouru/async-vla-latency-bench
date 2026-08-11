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
policy.n_action_steps = 25
request_threshold_actions = 25
```

Execution methods:

```text
naive_async
rtc
```

Do not use LIBERO-Plus/OOD environments during Stage 0.

### 2.1 Why `n_action_steps = 25` (amended 2026-08-11)

This was `10` for the first calibration run, which produced `d* = 100 ms` on a
curve that turned out to be measuring queue starvation rather than action
staleness.

LIBERO runs at 20 Hz, so one chunk of `H` actions covers `H x 50 ms` of robot
time. That is the total request latency the action queue can absorb before it
underruns and the arm holds position. At `H = 10` the budget is 500 ms against
~500 ms of measured native inference — no headroom at all, and RTC's ~660 ms is
already past it. The first run therefore held on ~33% (naive) to ~44% (RTC) of
control steps at **zero** added delay, rising to ~65-70% at +700 ms, and every
one of its 96 failures was a step-cap timeout rather than a task error.

`H = 25` gives a 1250 ms budget, which covers native plus the full amended delay
sweep. `request_threshold_actions` is raised from the section 16 default of
`ceil(H/2)` to `H` for the same reason: requesting only once the queue has half
drained spends half the budget before the request is even issued. Both values
apply identically to `naive_async` and `rtc`, preserving K009.

This changes the control regime, not just the plumbing — 25 steps of open-loop
execution per observation is a different condition from 10, and Days 1-3 results
(which ran at `H = 10`, with `execution_horizons: [2, 5, 10]` all deeper in the
same starvation regime) are **not** directly comparable to Stage 0 onward.

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

Test exactly five **added-delay** settings (amended 2026-08-11; was eight, to
`+700 ms`):

| `added_delay_ms` | Display label | Meaning |
|---:|---|---|
| `0` | **Native** | No artificial delay; measured model/runtime latency remains present |
| `100` | **Native + 100 ms** | Native request latency plus 100 ms |
| `200` | **Native + 200 ms** | Native request latency plus 200 ms |
| `300` | **Native + 300 ms** | Native request latency plus 300 ms |
| `400` | **Native + 400 ms** | Native request latency plus 400 ms |

Important:

- These values are **added artificial delay**, not total request latency.
- Log the actual measured total request latency for every request.
- Also convert total latency to effective logical delay in control steps.
- Do not use different delays for different task groups or execution methods.
- Observe the full degradation curve within this range, but do not automatically choose `+400 ms` if it is already saturated.

### 4.1 Why the sweep stops at `+400 ms` (amended 2026-08-11)

The cap is set by RTC, not by the horizon. RTC discards the leading
`delay_steps` actions of every chunk (they were already guided by the previous
chunk), so its usable chunk is `chunk_size - delay_steps` against a wait of
`delay_steps`. The queue therefore starves once `delay_steps` exceeds half the
raw chunk — 25 steps / 1250 ms for pi05's 50-action chunk — **at any
`n_action_steps`**. Raising `H` cannot buy past it.

RTC's measured inference runs ~660 ms at native and ~735 ms under delay, leaving
roughly 500 ms of addable delay before that ceiling and ~400 ms with margin
against its p95. Levels above that do not measure delay tolerance; they
re-measure queue starvation, which is what the `H = 10` calibration did.

`run_stage0.py` preflight asserts `chunk_size >= 2 x n_action_steps`, which is
the invariant this grid is derived from.

---

## 5. Seeds and total budget

Use six seeds (amended 2026-08-11; was two). Seeds `0` and `1` remain the pair
Stage 1 uses, so its ID controls are still drawn from Stage 0 episodes:

```text
seed = 0    (shared with Stage 1)
seed = 1    (shared with Stage 1)
seed = 10
seed = 11
seed = 12
seed = 13
```

The extra seeds deliberately skip `2-9`, which STAGE_2 section 4 reserves as
held-out confirmatory seeds. Calibrating `d*` on a held-out seed would weaken the
Stage 2 claim.

Calibration budget:

```text
3 tasks
× 2 methods
× 5 added-delay settings
× 6 seeds
= 180 episodes
```

There are **30 unique task × method × delay condition blocks**, each with 6 seeds.

The `Native` episodes and the episodes at the eventually selected `d*`, **restricted
to seeds 0 and 1**, become the Stage 1 shared ID controls — 24 episodes, unchanged.

Therefore:

```text
Stage 0 unique episodes = 180
Stage 1 OOD episodes    = 168
--------------------------------
Total unique episodes   = 348
```

Do not rerun the 24 selected ID low/high episodes unless a run is invalid.

**A change to `n_action_steps` or `request_threshold_actions` invalidates every
Stage 0 episode, including those 24.** They are the same execution condition as
Stage 1's ID arm only so long as the execution configuration is identical.

### 5.1 Why six seeds (amended 2026-08-11)

Two reasons, both structural rather than cosmetic:

1. **Viability becomes decidable.** Section 8.1 admits a cell at `Native success
   >= 1/2`. At two seeds a cell's native rate can only be `0`, `0.5`, or `1.0`,
   so admission turns on a single episode — and admission determines which cells
   the pooled curve is computed over, i.e. the curve `d*` is read off.
2. **`d*` is an order statistic, so noise biases it downward.** Section 8.3 takes
   the *smallest* qualifying delay. At six episodes per pooled point the standard
   error is ~20 points, the same size as the 20-point drop criterion, so the rule
   stops at whichever level dips first by chance. Six seeds (18 episodes per
   point) brings that to ~11 points.

Four seeds would be the bare minimum; six is chosen because the marginal cost is
~90 minutes of A100 time against a parameter that 168 Stage 1 and ~96-128 Stage 2
episodes are conditioned on, and which no amount of held-out replication can
repair after the fact.

---

## 6. Complete calibration experiment table

### 6.1 Condition-level matrix — 30 conditions

Generated from `benchmark/stage0.py`; enumerate with `python -m async_vla_benchmark.scripts.run_stage0 --config <cfg> --dry-run`.

| # | Task-demand group | Suite:task_id | Method | Added delay | Seeds | Episodes |
|---:|---|---|---|---|---|---:|
| 1 | Single-stage transport | `libero_spatial:2` | Naive async | Native | `0, 1, 10, 11, 12, 13` | 6 |
| 2 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 100 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 3 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 200 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 4 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 300 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 5 | Single-stage transport | `libero_spatial:2` | Naive async | Native + 400 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 6 | Single-stage transport | `libero_spatial:2` | RTC | Native | `0, 1, 10, 11, 12, 13` | 6 |
| 7 | Single-stage transport | `libero_spatial:2` | RTC | Native + 100 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 8 | Single-stage transport | `libero_spatial:2` | RTC | Native + 200 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 9 | Single-stage transport | `libero_spatial:2` | RTC | Native + 300 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 10 | Single-stage transport | `libero_spatial:2` | RTC | Native + 400 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 11 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native | `0, 1, 10, 11, 12, 13` | 6 |
| 12 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 100 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 13 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 200 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 14 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 300 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 15 | Articulated/contact-rich | `libero_goal:0` | Naive async | Native + 400 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 16 | Articulated/contact-rich | `libero_goal:0` | RTC | Native | `0, 1, 10, 11, 12, 13` | 6 |
| 17 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 100 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 18 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 200 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 19 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 300 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 20 | Articulated/contact-rich | `libero_goal:0` | RTC | Native + 400 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 21 | Multi-stage/sequential | `libero_10:2` | Naive async | Native | `0, 1, 10, 11, 12, 13` | 6 |
| 22 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 100 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 23 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 200 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 24 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 300 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 25 | Multi-stage/sequential | `libero_10:2` | Naive async | Native + 400 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 26 | Multi-stage/sequential | `libero_10:2` | RTC | Native | `0, 1, 10, 11, 12, 13` | 6 |
| 27 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 100 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 28 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 200 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 29 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 300 ms | `0, 1, 10, 11, 12, 13` | 6 |
| 30 | Multi-stage/sequential | `libero_10:2` | RTC | Native + 400 ms | `0, 1, 10, 11, 12, 13` | 6 |

### 6.2 Episode-level manifest — all 180 episodes

`Exp.` is the doc-level label; `run_id` in the emitted manifest is the descriptive form built by `Stage0Plan.run_id`.

| Exp. | Task-demand group | Suite:task_id | Method | Added delay (ms) | Delay label | Seed |
|---:|---|---|---|---:|---|---:|
| C001 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 0 |
| C002 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 1 |
| C003 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 10 |
| C004 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 11 |
| C005 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 12 |
| C006 | Single-stage transport | `libero_spatial:2` | Naive async | 0 | Native | 13 |
| C007 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 0 |
| C008 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 1 |
| C009 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 10 |
| C010 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 11 |
| C011 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 12 |
| C012 | Single-stage transport | `libero_spatial:2` | Naive async | 100 | Native + 100 ms | 13 |
| C013 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 0 |
| C014 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 1 |
| C015 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 10 |
| C016 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 11 |
| C017 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 12 |
| C018 | Single-stage transport | `libero_spatial:2` | Naive async | 200 | Native + 200 ms | 13 |
| C019 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 0 |
| C020 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 1 |
| C021 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 10 |
| C022 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 11 |
| C023 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 12 |
| C024 | Single-stage transport | `libero_spatial:2` | Naive async | 300 | Native + 300 ms | 13 |
| C025 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 0 |
| C026 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 1 |
| C027 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 10 |
| C028 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 11 |
| C029 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 12 |
| C030 | Single-stage transport | `libero_spatial:2` | Naive async | 400 | Native + 400 ms | 13 |
| C031 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 0 |
| C032 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 1 |
| C033 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 10 |
| C034 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 11 |
| C035 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 12 |
| C036 | Single-stage transport | `libero_spatial:2` | RTC | 0 | Native | 13 |
| C037 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 0 |
| C038 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 1 |
| C039 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 10 |
| C040 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 11 |
| C041 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 12 |
| C042 | Single-stage transport | `libero_spatial:2` | RTC | 100 | Native + 100 ms | 13 |
| C043 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 0 |
| C044 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 1 |
| C045 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 10 |
| C046 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 11 |
| C047 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 12 |
| C048 | Single-stage transport | `libero_spatial:2` | RTC | 200 | Native + 200 ms | 13 |
| C049 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 0 |
| C050 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 1 |
| C051 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 10 |
| C052 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 11 |
| C053 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 12 |
| C054 | Single-stage transport | `libero_spatial:2` | RTC | 300 | Native + 300 ms | 13 |
| C055 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 0 |
| C056 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 1 |
| C057 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 10 |
| C058 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 11 |
| C059 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 12 |
| C060 | Single-stage transport | `libero_spatial:2` | RTC | 400 | Native + 400 ms | 13 |
| C061 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 0 |
| C062 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 1 |
| C063 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 10 |
| C064 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 11 |
| C065 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 12 |
| C066 | Articulated/contact-rich | `libero_goal:0` | Naive async | 0 | Native | 13 |
| C067 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 0 |
| C068 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 1 |
| C069 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 10 |
| C070 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 11 |
| C071 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 12 |
| C072 | Articulated/contact-rich | `libero_goal:0` | Naive async | 100 | Native + 100 ms | 13 |
| C073 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 0 |
| C074 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 1 |
| C075 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 10 |
| C076 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 11 |
| C077 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 12 |
| C078 | Articulated/contact-rich | `libero_goal:0` | Naive async | 200 | Native + 200 ms | 13 |
| C079 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 0 |
| C080 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 1 |
| C081 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 10 |
| C082 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 11 |
| C083 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 12 |
| C084 | Articulated/contact-rich | `libero_goal:0` | Naive async | 300 | Native + 300 ms | 13 |
| C085 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 0 |
| C086 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 1 |
| C087 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 10 |
| C088 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 11 |
| C089 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 12 |
| C090 | Articulated/contact-rich | `libero_goal:0` | Naive async | 400 | Native + 400 ms | 13 |
| C091 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 0 |
| C092 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 1 |
| C093 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 10 |
| C094 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 11 |
| C095 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 12 |
| C096 | Articulated/contact-rich | `libero_goal:0` | RTC | 0 | Native | 13 |
| C097 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 0 |
| C098 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 1 |
| C099 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 10 |
| C100 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 11 |
| C101 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 12 |
| C102 | Articulated/contact-rich | `libero_goal:0` | RTC | 100 | Native + 100 ms | 13 |
| C103 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 0 |
| C104 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 1 |
| C105 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 10 |
| C106 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 11 |
| C107 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 12 |
| C108 | Articulated/contact-rich | `libero_goal:0` | RTC | 200 | Native + 200 ms | 13 |
| C109 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 0 |
| C110 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 1 |
| C111 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 10 |
| C112 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 11 |
| C113 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 12 |
| C114 | Articulated/contact-rich | `libero_goal:0` | RTC | 300 | Native + 300 ms | 13 |
| C115 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 0 |
| C116 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 1 |
| C117 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 10 |
| C118 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 11 |
| C119 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 12 |
| C120 | Articulated/contact-rich | `libero_goal:0` | RTC | 400 | Native + 400 ms | 13 |
| C121 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 0 |
| C122 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 1 |
| C123 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 10 |
| C124 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 11 |
| C125 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 12 |
| C126 | Multi-stage/sequential | `libero_10:2` | Naive async | 0 | Native | 13 |
| C127 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 0 |
| C128 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 1 |
| C129 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 10 |
| C130 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 11 |
| C131 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 12 |
| C132 | Multi-stage/sequential | `libero_10:2` | Naive async | 100 | Native + 100 ms | 13 |
| C133 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 0 |
| C134 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 1 |
| C135 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 10 |
| C136 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 11 |
| C137 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 12 |
| C138 | Multi-stage/sequential | `libero_10:2` | Naive async | 200 | Native + 200 ms | 13 |
| C139 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 0 |
| C140 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 1 |
| C141 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 10 |
| C142 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 11 |
| C143 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 12 |
| C144 | Multi-stage/sequential | `libero_10:2` | Naive async | 300 | Native + 300 ms | 13 |
| C145 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 0 |
| C146 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 1 |
| C147 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 10 |
| C148 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 11 |
| C149 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 12 |
| C150 | Multi-stage/sequential | `libero_10:2` | Naive async | 400 | Native + 400 ms | 13 |
| C151 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 0 |
| C152 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 1 |
| C153 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 10 |
| C154 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 11 |
| C155 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 12 |
| C156 | Multi-stage/sequential | `libero_10:2` | RTC | 0 | Native | 13 |
| C157 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 0 |
| C158 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 1 |
| C159 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 10 |
| C160 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 11 |
| C161 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 12 |
| C162 | Multi-stage/sequential | `libero_10:2` | RTC | 100 | Native + 100 ms | 13 |
| C163 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 0 |
| C164 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 1 |
| C165 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 10 |
| C166 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 11 |
| C167 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 12 |
| C168 | Multi-stage/sequential | `libero_10:2` | RTC | 200 | Native + 200 ms | 13 |
| C169 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 0 |
| C170 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 1 |
| C171 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 10 |
| C172 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 11 |
| C173 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 12 |
| C174 | Multi-stage/sequential | `libero_10:2` | RTC | 300 | Native + 300 ms | 13 |
| C175 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 0 |
| C176 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 1 |
| C177 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 10 |
| C178 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 11 |
| C179 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 12 |
| C180 | Multi-stage/sequential | `libero_10:2` | RTC | 400 | Native + 400 ms | 13 |

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
Native success >= 1 / 2
```

Cells already at `0 / 2` under Native are retained in all tables but are not allowed to determine the high-delay choice because they are already at floor.

### 8.2 Compute calibration summary

For each candidate:

```text
d ∈ {100, 200, 300, 400} ms
```

using only the viable cells, calculate:

```text
S_native
S_d
delay_drop(d) = S_native - S_d
```

where success is pooled over the same viable task × method cells and all six seeds.

`delay_drop` is stated as `S_native - S_d` so a degradation is a positive number,
matching the `S_native - S_d >= 0.20` test in section 8.3. (It read `S_d -
S_native` before 2026-08-11, which contradicted 8.3; the implementation in
`benchmark/stage0.py` always used the 8.3 orientation.)

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

3. Otherwise choose the **largest candidate delay** — `400 ms` under the section 4
   grid as amended — and flag:

```text
CALIBRATION_WEAK = true
```

The flags describe the calibration result; they are not reasons to retune using OOD data.

`benchmark/stage0.py` implements fallback 3 as `max(candidates)` rather than a
literal `700`, so it tracks section 4 automatically. The flags are additionally
derived from the shape of the curve rather than from whichever branch fired, so a
flat or floored curve is always labelled even when fallback 1 claims it first.

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

| Task-demand group | Method | Native | +100 | +200 | +300 | +400 ms | Viable? |
|---|---|---:|---:|---:|---:|---:|---|

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

Mark the selected `d*`.

---

### Table C — Execution-method calibration

| Method | Native | +100 | +200 | +300 | +400 ms |
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
