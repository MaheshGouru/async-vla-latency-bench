# Days 1-3 Report

Answers the twelve questions in `docs/DAYS_1_3_SPEC.md` section 24, and records the
go/no-go assessment required by section 25.

> **This report describes the run of 2026-08-07/08, not the earlier 2026-08-06 dataset.**
> Every `naive_async` and `rtc` result published before 2026-08-07 is withdrawn: RTC
> guidance was never active in those runs and `request_threshold_actions` was `8` rather
> than the `5` that section 15 specifies. See "Superseded results" at the end. The data
> behind this report currently lives on the Modal volume `async-vla-benchmark-outputs`;
> the CSVs in this directory are refreshed by `scripts/aggregate_results.py`.

## Provenance

| item | value |
| --- | --- |
| LeRobot commit | `2aba372b4e217cc47db28e0f836859b20d1456c9` |
| Checkpoint | `lerobot/pi05_libero_finetuned` @ `8e174154ef5f6c60a8da12ae99c303d8963138c1` |
| GPU | NVIDIA A100-SXM4-40GB, CUDA 13.0 |
| Packages | lerobot 0.6.1, torch 2.11.0, mujoco 3.8.1, robosuite 1.4.0 |
| Recorded deviations | none |
| Tasks | `libero_spatial:0`, `libero_goal:0`, `libero_10:0` |
| Control period | 50 ms (20 Hz) |
| Episodes | 222 unique (150 core + 108 horizon-sweep, 36 shared h=10 cells) |
| Requests | 3998, all CUDA-synchronized |
| Validation | `validate_results.py`: 0 errors |

Seeds are `[0,1,2,3,4]` for the core experiment and `[0,1,2]` for the horizon sweep,
giving n=15 per core cell and n=9 per sweep cell.

---

## 1. Native p50, p95, and p99 request latencies

**Authoritative**, from the section 7 profiling pass (10 warmup + 100 measured requests,
CUDA-synchronized):

| statistic | value (ms) |
| --- | --- |
| p50 | **476.8** |
| p95 | **489.9** |
| p99 | **499.8** |
| mean ± std | 478.4 ± 6.6 |

The distribution is tight (std 6.6 ms, range 469.0-500.6). Decomposition: model inference
474.1 ms (99.1%), preprocessing 3.6 ms, postprocessing 0.6 ms. The CUDA event time
(p50 472.5 ms) matches the model wall-clock time (p50 472.6 ms) to 0.1 ms, confirming the
measurement is genuinely synchronized as section 7 requires.

In-run request latencies, measured across the benchmark's own 3998 requests:

| population | n | p50 | p95 | p99 | mean |
| --- | --- | --- | --- | --- | --- |
| non-RTC strategies | 2521 | 497.2 | 524.7 | 559.4 | 499.6 |
| RTC | 1477 | 637.7 | 706.2 | 828.0 | 639.7 |

RTC guidance adds **+28%** to request latency (637.7 vs 497.2 ms p50), the single largest
cost attributable to any strategy in this benchmark.

**On cross-run stability.** The dedicated profiles from 2026-08-06 and 2026-08-08 agree to
within **+3.6%** (460.1 → 476.8 ms p50), so inference speed on the pinned stack is stable.
What differs is the *in-run* latency: the 2026-08-06 run recorded ~400 ms in-run against
its own 460 ms profile — 13% **below** it, which should not occur, since in-run requests
carry environment overhead a clean profile does not. This run is self-consistent
(497 ms in-run against a 477 ms profile, +4%) and stable within itself (quartile means
510.6 → 496.6 ms). The discrepancy is therefore a property of the superseded dataset, not
evidence of a drifting stack; it is one more reason not to compare against it.

## 2. Control steps occupied by native inference

At a 50 ms control period, `latency_to_delay_steps` uses `ceil`. Median in-run
`delay_steps`, separated by strategy because RTC's guidance cost shifts it:

| strategy | native | native_plus_300 | native_plus_700 |
| --- | --- | --- | --- |
| blocking_sync, naive_async | **10** | 16 | 24 |
| rtc | **13** | 19 | 27 |

The authoritative profile (question 1, p50 476.8 ms) also converts to **10** steps,
consistent with the non-RTC in-run figure.

**This is the single most important number in the report.** Native inference occupies
**10 control steps** — exactly the core experiment's execution horizon of 10 — and
**13** steps once RTC guidance is enabled:

```
delay / chunk  =  10/10 = 1.00   (blocking_sync, naive_async)
               =  13/10 = 1.30   (rtc)
```

A chunk is fully consumed in the time it takes to produce its replacement, so the queue is
guaranteed to reach empty before a new chunk arrives, and RTC's replacement arrives three
steps *after* the queue has already run dry. Every asynchronous strategy is operating at
or beyond the boundary of the regime it was designed for. `discarded_old_actions` is 0 in
all 222 episodes, confirming this directly: there was never a surplus action to discard.

## 3. Action age versus raw inference latency

| strategy | mean action age (ms) | mean request latency (ms) | ratio | max action age (ms) |
| --- | --- | --- | --- | --- |
| ideal_sync | 221.0 | 511.8 | 0.43 | 450.0 |
| blocking_sync | 383.9 | 505.1 | 0.76 | 1351.1 |
| naive_async | 471.5 | 500.5 | 0.94 | 1342.2 |
| rtc | 474.4 | 640.8 | 0.74 | 1548.9 |

Action age is **not** higher than request latency in this run — it is 0.74-0.94x for the
async strategies. This reverses the earlier dataset, where async action age exceeded
latency by ~1.4-1.5x, and the mechanism is question 2: because the queue empties before
each replacement arrives, executed actions are drawn from the *front* of a fresh chunk far
more often than from the tail of a buffered one. Buffering deep enough to accumulate
staleness never happens. Tail staleness is still severe — max action age reaches 1.3-1.5 s.

## 4. Does asynchronous buffering prevent blocking pauses?

**No, not at this operating point.**

| strategy | hold steps | environment steps | hold fraction |
| --- | --- | --- | --- |
| ideal_sync | 0.0 | 154.8 | 0% |
| blocking_sync | 212.4 | 338.2 | 63% |
| naive_async | 182.2 | 357.4 | 51% |
| rtc | 208.0 | 365.0 | 57% |

`naive_async` reduces hold steps only from 63% to 51%. Asynchronous buffering is supposed
to eliminate the blocking pause; here it removes about a fifth of it, because inference
outlasts the chunk (question 2) and the queue underruns regardless.

## 5. Does naive buffering increase stale-action execution?

**No.** `naive_async` max action age (1342 ms) is essentially identical to `blocking_sync`
(1351 ms), and `discarded_old_actions` is 0 everywhere. There is no accumulated buffer to
go stale — the same mechanism as questions 2 and 3. This question cannot be answered
meaningfully until the horizon exceeds the inference delay.

## 6. Does RTC improve task success over naive asynchronous replacement?

**No. RTC is worse.** Success rate with Wilson 95% intervals, n=15 per cell:

| strategy | native | native+300 | native+700 |
| --- | --- | --- | --- |
| ideal_sync | 1.000 [0.796, 1.000] *(ideal profile)* | — | — |
| blocking_sync | **0.933** [0.702, 0.988] | 0.267 [0.109, 0.520] | 0.267 [0.109, 0.520] |
| naive_async | 0.267 [0.109, 0.520] | 0.133 [0.037, 0.379] | 0.000 [0.000, 0.204] |
| rtc | 0.067 [0.012, 0.298] | 0.000 [0.000, 0.204] | 0.000 [0.000, 0.204] |

Two points of interpretive discipline:

1. **The intervals overlap.** At n=15, `rtc` 0.067 [0.012, 0.298] and `naive_async` 0.267
   [0.109, 0.520] are not separated. The claim "RTC reduces success" is **not** supported
   by these success rates alone. It is supported by the mechanism below.
2. **`blocking_sync` beats every asynchronous strategy at native latency** (0.933 vs
   0.267 vs 0.067). At this operating point, waiting is better than any form of async
   execution — the headline result of Days 1-3.

The mechanism, which *is* measured directly: RTC costs +28% inference latency
(question 1), which pushes delay_steps from 11 to 13, while contributing zero guided
actions (question 7). It pays the full price of guidance and receives none of it.

## 7. Does RTC primarily improve continuity, freshness, or both?

**Continuity only.**

Bootstrap 95% intervals on the relative difference, 10000 resamples, n=45 episodes per
strategy (all latency profiles pooled):

| metric | naive_async | rtc | change | 95% CI |
| --- | --- | --- | --- | --- |
| mean action delta L2 | 0.3136 | 0.2223 | **−29.1%** | [−39.6%, −16.8%] |
| mean action acceleration L2 | 0.1397 | 0.1083 | **−22.5%** | [−34.2%, −8.5%] |
| mean action jerk L2 | 0.2648 | 0.2023 | **−23.6%** | [−34.6%, −10.2%] |
| mean action age (freshness) | 471.5 ms | 474.4 ms | +0.6% | [+0.0%, +1.2%] |

All three continuity intervals exclude zero with substantial margin: **the smoothing
effect is real, not noise**, and it is the only positive result RTC produces in this
benchmark. The action-age interval technically excludes zero, but the effect is 2.9 ms —
statistically detectable at n=45 and practically negligible against a 50 ms control
period.

This is exactly the pattern section 25 lists as a *continue* criterion ("RTC improves
continuity but leaves measurable freshness limitations"), and unlike the success-rate
comparison in question 6, it is supported by intervals rather than point estimates alone.

**The continuity gain arrives without any guided actions.** Across all 81 RTC episodes
and all 1477 RTC requests, `rtc_guided_actions` sums to **0**, at every horizon
(h=2, 5, 10). The reason is arithmetic:

```
guided = effective_horizon − min(inference_delay, effective_horizon)
effective_horizon = min(execution_horizon, overlap) ,  overlap ≈ ceil(h/2) ≤ 5
inference_delay = 13 steps  ≥  effective_horizon  ⇒  guided ≡ 0
```

Measured: `rtc_mean_effective_execution_horizon` = **4.67** against a configured **10** —
LeRobot clamps the horizon to the remainder length, which resolves the open risk carried
in `days1_3_audit.md`. The `inference_delay` estimate disagrees with the realized delay on
**37%** of requests (mean absolute error 1.75 steps), a reportable deviation from
section 15's requirement that the current request's own latency be used, which is not
knowable before the request completes.

Since no *softly guided* action is ever executed, the continuity improvement must come
from chunk-level conditioning on the previous chunk's remainder rather than from the
guidance window itself. The 24-29% reduction is measured; that mechanism is inferred and
is not independently confirmed here.

## 8. Queue underrun frequency

| strategy | underrun steps | environment steps | fraction |
| --- | --- | --- | --- |
| ideal_sync | 0.0 | 154.8 | 0% |
| blocking_sync | 212.4 | 338.2 | 63% |
| naive_async | 182.2 | 357.4 | 51% |
| rtc | 208.0 | 365.0 | 57% |

Underruns dominate every non-ideal condition. `queue_underrun_steps` equals
`hold_action_steps` in every episode, as expected: an underrun is precisely a step with no
queued action.

## 9. Best fixed execution horizon per task

Horizon sweep, `naive_async`, success rate (n=9 per cell, native and native+700 pooled):

| task | h=2 | h=5 | h=10 |
| --- | --- | --- | --- |
| libero_spatial | 0.000 | **0.500** | 0.000 |
| libero_goal | 0.000 | 0.167 | **0.500** |
| libero_10 | 0.000 | 0.000 | 0.000 |

For `rtc`, every cell is 0.000 at every horizon and every task.

## 10. Is one fixed horizon consistently optimal?

**No.** `h=5` is best for `libero_spatial` (0.500), `h=10` is best for `libero_goal`
(0.500), and no horizon produces a single success on `libero_10`. `h=2` fails everywhere —
expected, since a 2-step chunk expires roughly 5x faster than inference can replace it.

The task-dependence is real but rests on n=9 per cell; these should not be treated as
precise optima.

## 11. Are the differences large enough to justify adding VLASH and FASTER?

**Yes, but not for the reason the question anticipates.** The gap that matters is not
between async methods — it is between `ideal_sync` (1.000) and every latency-exposed
strategy (0.000-0.267 at native+300 and beyond). There is a large amount of headroom, and
the current asynchronous approaches recover almost none of it.

However, the more actionable finding is that **the operating point, not the method, is the
binding constraint**. With inference occupying 10 control steps against a 10-step horizon
(13 with RTC),
no chunk-based async method can work. Adding VLASH and FASTER at this configuration would
likely reproduce the same null. Raising `policy_n_action_steps` from 10 to the
checkpoint's native 50 should precede any new method:

| horizon | threshold | delay | guided actions |
| --- | --- | --- | --- |
| 10 (current) | 5 | 13 | 0 |
| 20 | 10 | 13 | 0 |
| 30 | 15 | 13 | 2 |
| 50 | 25 | 13 | **12** |

## 12. Remaining implementation and reproducibility problems

1. **The superseded run's in-run latency is unexplained.** The 2026-08-06 dataset recorded
   ~400 ms in-run against its own 460 ms dedicated profile — 13% below a measurement that
   should be a lower bound. The current run is self-consistent (497 vs 477 ms) and the two
   dedicated profiles agree to +3.6%, so this does not affect any result reported here,
   but the mechanism was never identified and is worth understanding before trusting any
   pre-2026-08-07 latency figure.
2. **Native inference occupies the entire execution horizon** (10 steps against h=10, 13
   with RTC). This is the binding constraint on the whole Days 1-3 matrix rather than a
   defect, but it means the async strategies are not being evaluated in the regime they
   target. See question 11.
3. **RTC contributes zero guided actions** at every horizon in the spec's matrix. RTC is
   validated as *running* but cannot be evaluated as a *method* at this configuration.
4. **`inference_delay` estimation error**: mismatched on 37% of requests, mean absolute
   error 1.75 steps. Section 15's exact requirement is unsatisfiable by construction.
5. **Wide intervals at n=15 for success rates.** Most pairwise success comparisons are not
   separated. Claims should rest on mechanism (guided-action counts, delay/horizon ratios)
   or on the continuous metrics, where bootstrap intervals at n=45 are tight enough to
   exclude zero (question 7).
6. **High timeout rates**: `blocking_sync` 51%, `naive_async` 87%, `rtc` 98% of episodes
   hit the step cap. Most non-ideal episodes end by timeout rather than task outcome, so
   success rates partly measure "finished in time".
7. **Residual non-determinism ~3%** from GPU/cuDNN floating point, not eliminated by
   per-episode `torch.manual_seed`. `ideal_sync` nonetheless reproduced exactly against
   the 2026-08-06 run (1.000 success, 154.8 mean steps), bounding the instability to
   latency-sensitive paths.

---

## Go/no-go assessment (section 25)

Continue when at least three hold:

| criterion | verdict |
| --- | --- |
| success degradation differs across latency profiles | **yes** — 0.933 → 0.267 → 0.267 |
| naive async and RTC have meaningfully different outcomes | **yes** — continuity −29%, success differs (intervals overlap) |
| action age differs substantially from raw request latency | **no** — 0.94x for naive_async |
| queue underruns occur under realistic or stress latency | **yes** — 51-63% of steps |
| fixed horizon changes the success-latency trade-off | **yes** — 0.000 / 0.500 / 0.000 across h |
| no single horizon uniformly optimal | **yes** — h=5 spatial, h=10 goal |
| RTC improves continuity but leaves freshness limitations | **yes** — exactly the measured pattern |

**Six of seven hold; the bar is three. Recommendation: continue.**

One stop-or-reframe condition also fires: *"action age is nearly identical for naive async
and RTC"* (471.5 vs 474.4 ms). This is an accurate description of the data and should be
treated as a scoping signal — the freshness dimension of the RTC comparison is not
measurable at this operating point, though the continuity dimension is.

The stop conditions that do **not** fire: ideal baseline success is strong (1.000); the
strategies are not nearly identical; native latency is not negligible relative to the
horizon (it exceeds it); the horizon sweep has a measurable effect; and RTC is now
reproduced and validated in the current stack.

## Superseded results

The following claims from the pre-2026-08-07 version of this report are **withdrawn**:

- "RTC achieves 93.3% success at native latency versus 33.3% for naive_async." Those
  `rtc` episodes ran without guidance; the figure was produced by delay-aligned chunk
  truncation in `execution.py`. The corrected value is **6.7%**.
- The question 6 answer asserting RTC improves success. It does not.
- Any comparison of action age against request latency using the earlier ratios (~1.4-1.5x),
  which do not reproduce (see question 3).
- All in-run latency figures from the 2026-08-06 dataset, which sat 13% below that run's
  own dedicated profile (see question 1). Its *dedicated* profile (460.1 ms p50) remains
  consistent with this run's (476.8 ms, +3.6%).

`blocking_sync` and `ideal_sync` conclusions from the earlier dataset were unaffected by
the RTC and threshold defects, but their absolute latencies are still subject to the drift
in question 1 and have been regenerated here regardless.
