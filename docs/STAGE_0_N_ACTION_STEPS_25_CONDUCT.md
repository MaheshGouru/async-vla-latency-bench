# Stage 0 Conduct: `n_action_steps=25` Exploratory Rerun

## Status and purpose

This document records how the result bundle at:

```text
/Users/tejasrikurapati/Downloads/stage0
```

was actually conducted. It is a retrospective methods record based on the run
log, episode summaries, request traces, and action traces in that bundle. It
must not be read as the original frozen Stage 0 protocol.

The rerun changed the policy execution setting from `n_action_steps=10` to
`n_action_steps=25` after the initial calibration in:

```text
/Users/tejasrikurapati/Downloads/stage0 2
```

showed poor ID success. This decision used ID results only; no OOD results were
used.

## Comparison with the initial `n_action_steps=10` run

The fair direct comparison uses the 60 cells shared by both bundles:

```text
3 tasks
x 2 methods
x 5 added delays (0, 100, 200, 300, 400 ms)
x 2 seeds (0, 1)
= 60 matched episodes
```

| Comparison | `n_action_steps=10` | `n_action_steps=25` | Difference |
|---|---:|---:|---:|
| All 60 matched episodes | 8/60 (13.3%) | 30/60 (50.0%) | +36.7 points |
| Naive async | 7/30 (23.3%) | 8/30 (26.7%) | +3.3 points |
| RTC | 1/30 (3.3%) | 22/30 (73.3%) | +70.0 points |
| Native only | 4/12 (33.3%) | 7/12 (58.3%) | +25.0 points |

Across matched episodes, the `n_action_steps=25` run converts 27 failures from
the `n_action_steps=10` run into successes, while five cells change in the
opposite direction. The improvement is therefore real in the observed data,
but it is overwhelmingly an RTC improvement. Naive async is nearly unchanged.

By task over matched delays and seeds:

| Task | `n_action_steps=10` | `n_action_steps=25` |
|---|---:|---:|
| Single-stage transport | 1/20 (5%) | 10/20 (50%) |
| Articulated/contact-rich | 5/20 (25%) | 13/20 (65%) |
| Multi-stage/sequential | 2/20 (10%) | 7/20 (35%) |

This establishes that the `n_action_steps=25` bundle has better raw ID success
on the shared conditions. It does not establish that 25 is universally better,
because the setting was chosen after inspecting the initial ID outcomes and
only two matched seeds are available.

## Evaluated policy and action configuration

The run log records:

```text
policy = lerobot/pi05_libero_finetuned
policy.n_action_steps = 25
policy.chunk_size = 50
fixed execution horizon = 25 actions
control frequency = 20 Hz
control period = 50 ms
```

The run log names one policy checkpoint for the rerun, but the downloaded result
summaries do not contain a checkpoint revision SHA or repository SHA. The exact
revision and whether it matches the initial bundle therefore cannot be verified
from the downloaded artifacts alone.

The same horizon of 25 actions was used for Naive async and RTC. This matters:
the rerun is a different execution configuration, not merely an additional
replicate of the `n_action_steps=10` experiment.

## ID tasks

Only standard LIBERO ID tasks were used:

| Task-demand group | Suite and ID | Exact task name |
|---|---|---|
| Single-stage transport | `libero_spatial:2` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate` |
| Articulated/contact-rich | `libero_goal:0` | `open_the_middle_drawer_of_the_cabinet` |
| Multi-stage/sequential | `libero_10:2` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it` |

The preflight log confirms all three suite IDs resolved to these exact names.
No LIBERO-Plus or other OOD environments were used.

## Factorial coverage

The rerun contains:

```text
3 tasks
x 2 execution methods
x 5 added-delay settings
x 6 seeds
= 180 episodes
```

Execution methods:

```text
naive_async
rtc
```

Seeds:

```text
0, 1, 10, 11, 12, 13
```

Added logical delays:

```text
0, 100, 200, 300, 400 ms
```

The planned `500`, `600`, and `700 ms` conditions were not run. The bundle is
therefore a denser-seed, truncated-delay exploratory calibration rather than the
96-episode matrix in `STAGE_0_LATENCY_CALIBRATION.md`.

## Discrete logical-time execution

The run used a 20 Hz logical control clock. Artificial delay was not implemented
with `sleep()`.

For each non-startup policy request:

```text
total logical latency
    = measured request latency + added delay

delay_steps
    = ceil(total logical latency / 50 ms)

response_available_step
    = request_step + delay_steps
```

Each episode began with an explicitly ideal startup request so that the action
queue was initially populated. The configured added delay applied to subsequent
requests. At most one policy request was outstanding.

When a delayed response became available, its action chunk was installed using
the execution-method-specific queue logic. The queue was not cleared at an
intervention because Stage 0 contains no interventions.

## Naive async execution

Naive async executed queued actions while one request was in flight. When the
new 50-action policy chunk became available, the queue used the first 25 actions
as the configured execution horizon and discarded obsolete queued actions as
defined by the runner.

The complete six-seed success counts were:

| Task | Native | +100 ms | +200 ms | +300 ms | +400 ms |
|---|---:|---:|---:|---:|---:|
| Single-stage transport | 0/6 | 0/6 | 0/6 | 0/6 | 0/6 |
| Articulated/contact-rich | 6/6 | 4/6 | 4/6 | 4/6 | 3/6 |
| Multi-stage/sequential | 0/6 | 0/6 | 0/6 | 0/6 | 0/6 |

Thus, increasing `n_action_steps` did not resolve the Native floor for two of
the three Naive async task cells.

## RTC execution

RTC used the installed policy's `predict_action_chunk` interface with:

```text
inference_delay = request-specific delay_steps
prev_chunk_left_over = current queue remainder
execution_horizon = 25
```

The complete six-seed success counts were:

| Task | Native | +100 ms | +200 ms | +300 ms | +400 ms |
|---|---:|---:|---:|---:|---:|
| Single-stage transport | 6/6 | 6/6 | 5/6 | 6/6 | 6/6 |
| Articulated/contact-rich | 4/6 | 4/6 | 4/6 | 4/6 | 3/6 |
| Multi-stage/sequential | 5/6 | 5/6 | 3/6 | 3/6 | 5/6 |

The improvement over `n_action_steps=10` is mainly attributable to this RTC
configuration.

## Episode limits and runtime environment

The run logs and episode records show task-dependent maximum lengths:

```text
Single-stage transport:     280 steps
Articulated/contact-rich:   300 steps
Multi-stage/sequential:     520 steps
```

All episode summary rows identify the GPU as:

```text
NVIDIA A100-SXM4-40GB
```

Measured request latency remained present in every condition. The added delay
was logical and did not inflate the wall-clock model latency measurement.

## Logged outputs

The bundle contains:

- 180 episode JSON summaries;
- 180 request Parquet traces;
- 180 executed-action Parquet traces;
- `latency_calibration_episode_results.csv`;
- per-task, pooled, method, and freshness tables;
- native-latency summaries and figures;
- `selected_high_delay.json`;
- the run log and Python package freeze.

The action traces preserve chunk and source-observation IDs for policy actions,
action age, queue depth, and hold/underrun flags. Request traces preserve measured
latency components, added delay, discrete delay steps, availability steps, and
RTC-specific fields.

## Delay selection performed in the bundle

Using all six seeds and the four viable Native task-method cells, the bundle
selected:

```text
d* = 200 ms
Native pooled success = 21/24 = 87.5%
+200 ms pooled success = 16/24 = 66.7%
drop = 20.8 percentage points
```

This satisfies the numerical primary rule for the revised six-seed analysis.
However, it does not follow the original frozen two-seed selection protocol.
Using only seeds 0 and 1 from this same bundle, `+200 ms` has 7/8 success, equal
to Native, while `+300 ms` has 5/8 success and is the first observed qualifying
delay. Therefore `200 ms` must be described as the result of the six-seed revised
protocol, not as the output of the original Stage 0 specification.

## Validation limitations

The following limitations remain and must accompany use of this bundle:

1. `n_action_steps=25` was selected after seeing poor ID performance at 10.
2. The delay grid stops at 400 ms.
3. The seed count differs from the frozen Stage 0 specification.
4. Repository SHA, checkpoint revision, and environment fingerprint are absent
   from the episode summary table.
5. Twenty-three hold/underrun actions in seven episodes have null chunk and
   source-observation IDs. Under the current canonical provenance invariant,
   those episodes should not have been marked valid without an explicit schema
   exception for holds.
6. The comparison has only two matched seeds per cell and should be reported as
   exploratory rather than as a definitive horizon ablation.

## Required interpretation

The defensible conclusion is:

> On the 60 directly matched ID episodes, the `n_action_steps=25` execution
> configuration produced substantially higher success than `n_action_steps=10`,
> primarily by improving RTC. This motivated adopting 25 as a revised candidate
> execution horizon before OOD evaluation.

Do not write that the original `n_action_steps=10` calibration was reproduced or
that the bundled `d*=200 ms` came from the original frozen two-seed rule.


---

## Follow-up consequence — 2026-08-16

The 10-action versus 25-action difference is no longer treated only as a
calibration nuisance. Stage 2 explicitly characterizes `n_action_steps × latency`
on ID tasks.

The 25-action Stage 1 operating point remains frozen and valid for Stage 1, but
the final paper must disclose that temporal action coverage is itself a major
experimental variable.
