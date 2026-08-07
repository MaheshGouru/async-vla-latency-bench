# Days 1-3 Report: π0.5-LIBERO Asynchronous Execution Benchmark

**Checkpoint:** `lerobot/pi05_libero_finetuned` (revision `main` — not yet pinned to a SHA, see limitations)
**LeRobot commit:** `2aba372b4e217cc47db28e0f836859b20d1456c9` (pinned)
**GPU:** NVIDIA A100-SXM4-40GB
**Tasks:** one selected task per suite — `libero_spatial:0`, `libero_goal:0`, `libero_10:0`
**Core experiment:** 150 episodes (3 tasks × [1 ideal + 9 delayed conditions] × 5 seeds)
**Horizon sweep:** 108 episodes (3 tasks × 2 strategies × 2 profiles × 3 horizons × 3 seeds)
**Validation:** `validate_results.py` passes on all 222 unique executed episodes (0 errors)

---

## 1. What are the native p50, p95, and p99 request latencies?

From `native_latency.json` (10 warm-up + 100 measured requests, single container):

| stat | value |
|---|---|
| mean | 459.3 ms |
| std | 6.0 ms |
| p50 | 460.1 ms |
| p90 | 466.6 ms |
| p95 | 467.2 ms |
| p99 | 469.9 ms |

Latency is tight and low-variance (std of 6ms on a ~460ms mean) — this A100 instance's inference cost is highly consistent request-to-request.

## 2. How many control steps does native inference occupy?

Control frequency is 20Hz (50ms/step). Using `ceil(latency_ms / 50)`:

| stat | latency | steps occupied |
|---|---|---|
| p50 | 460.1 ms | 10 steps |
| p95 | 467.2 ms | 10 steps |
| p99 | 469.9 ms | 10 steps |

Every measured request — even at p99 — occupies exactly 10 control steps. This matters directly: with `fixed_horizon=10`, native-latency chunks are only just barely long enough to cover their own generation time, leaving almost no slack. This is the mechanism behind several results below.

## 3. How much higher is action age than raw inference latency?

| strategy | profile | mean action age | mean request latency | ratio |
|---|---|---|---|---|
| `ideal_sync` | ideal | 221.0 ms | 402.5 ms | 0.55x |
| `blocking_sync` | native | 343.9 ms | 402.9 ms | 0.85x |
| `blocking_sync` | native+700 | 403.8 ms | 402.0 ms | 1.00x |
| `naive_async` | native | 602.4 ms | 398.0 ms | **1.51x** |
| `rtc` | native | 585.5 ms | 401.8 ms | **1.46x** |

Action age and raw request latency are meaningfully different quantities, not proxies for one another. `ideal_sync` shows the biggest gap in the other direction (age well under raw latency, since ideal responses are logically instantaneous — the "latency" here is just measured wall-clock model time, irrelevant to what the robot actually experiences). The async strategies show the opposite and more important effect: actions are **~1.5x older** than the raw request latency that generated them, because actions execute throughout the buffered chunk, not just the instant the response arrives. Request latency alone would substantially understate how stale the information controlling the robot actually is.

## 4. Does asynchronous buffering prevent blocking pauses?

Partially. Hold/underrun steps as a fraction of episode length:

| strategy | hold fraction |
|---|---|
| `blocking_sync` | 59.8% |
| `naive_async` | 34.9% |
| `rtc` | 39.7% |

Both async strategies roughly halve the fraction of the episode spent frozen compared to `blocking_sync`. But "prevent" would overstate it — over a third of every async episode is still spent holding, because `fixed_horizon=10` chunks only barely outlast the ~460ms/10-step native request latency (see Q2), so the queue still runs dry constantly even when requests are issued early.

## 5. Does naive buffering increase stale-action execution?

Indirectly, yes, via action age (Q3): `naive_async` has the highest mean action age of any strategy at every latency profile (602ms at native, still 531ms at +700ms) — actions are, on average, older under naive buffering than any other strategy including blocking. Days 1-3 doesn't instrument explicit "stale action" counts relative to a scene-change event (that's introduced in Days 4-8); action age is the available proxy here, and it points the same direction.

## 6. Does RTC improve task success over naive asynchronous replacement?

Yes, substantially, but only up to a point:

| profile | naive_async | rtc |
|---|---|---|
| native | 33.3% | **93.3%** |
| native+300ms | 26.7% | 20.0% |
| native+700ms | 0.0% | 0.0% |

At `native` latency, RTC's guidance clearly helps (93.3% vs 33.3%). At `native+300ms`, that advantage **inverts** — RTC is slightly worse than naive_async (20.0% vs 26.7%). Root cause investigated during this project: RTC's `execution_horizon` (configured at 10) gets silently clamped down to the queue-remainder length by LeRobot's own guidance code, and `request_threshold_actions` (currently shared between `naive_async` and `rtc`) determines how large that remainder is at request time — under added latency, the clamp leaves too little of the chunk under genuine guided blending. This is flagged as an unresolved tuning question, not a settled negative result for RTC.

## 7. Does RTC primarily improve continuity, freshness, or both?

Continuity, not freshness — cleanly separable in the data:

| profile | metric | naive_async | rtc |
|---|---|---|---|
| native | mean action age | 602.4 ms | 585.5 ms (~3% lower) |
| native | mean jerk | 0.315 | 0.300 (~5% lower) |
| native | queue underrun steps | 11.7 | 8.8 (~25% lower) |
| native+300 | queue underrun steps | 139.5 | 133.6 (~4% lower) |

RTC's action-age advantage over `naive_async` is marginal (a few percent) at every profile — it is **not** meaningfully fresher. Its queue-underrun count is consistently and more substantially lower, and jerk is consistently lower too. RTC's benefit is smoother, more continuous execution (fewer freezes, less jerky motion), not fresher information — matching the mechanism (guided blending reduces abrupt chunk transitions; it doesn't reduce how old the underlying observation is).

## 8. How frequently does each method experience queue underruns?

| strategy | mean underrun steps/episode | as % of episode |
|---|---|---|
| `ideal_sync` | 0.0 | 0.0% |
| `blocking_sync` | 195.8 | 59.8% |
| `naive_async` | 121.6 | 34.9% |
| `rtc` | 118.6 | 39.7%* |

(*RTC's underrun *count* is lower than naive_async's, but its episodes are also shorter on average — mostly because RTC succeeds and terminates early more often at `native`, which mechanically raises the underrun percentage of what remains. The raw step count, not the percentage, is the fairer continuity comparison here — see Q7.)

`ideal_sync` never holds by construction (zero logical latency). Every other strategy holds for a large fraction of every episode, underscoring how tight `fixed_horizon=10` is relative to native latency (Q2).

## 9. Which fixed execution horizon performs best for each task?

Aggregated across the 3 selected tasks (horizon sweep results):

| strategy | h=2 | h=5 | h=10 |
|---|---|---|---|
| `naive_async` (native) | 0.0% | 33.3% | 33.3% |
| `rtc` (native) | 11.1% | 22.2% | **100.0%** |
| both (native+700) | 0.0% | 0.0% | 0.0% |

`h=10` dominates at `native` latency for both strategies — for `rtc` dramatically so (100% vs 11-22%). Mechanistically: `h=2`/`h=5` chunks cover 100ms/250ms of execution against a ~460ms request delay, so the queue is starved almost every step regardless of strategy; `h=10` (~500ms coverage) is the only tested value that comes close to matching the delay.

## 10. Is one fixed horizon consistently optimal across tasks and latency profiles?

Not fully — `h=10` is optimal (or tied) at every tested `native` condition, but **no horizon tested works at `native+700ms`**, including `h=10`. The reason is the same mechanism as Q9: even the largest tested horizon (~500ms coverage) doesn't reach the ~1.1s round-trip delay at `+700ms`. The honest answer is "h=10 is the best of three insufficient options," not "h=10 solves the problem" — the real open question (untested here) is whether a horizon large enough to exceed `+700ms`'s delay would change this, since `policy_n_action_steps` could go as high as the model's native `chunk_size` (50), far beyond what was swept.

## 11. Are the differences large enough to justify adding VLASH and FASTER?

Yes, per the spec's own go/no-go criteria (§25): methods differ sharply (0-100% success range under matched conditions), horizons differ sharply (`h=10` vs `h=2`/`h=5`), RTC shows the "improves continuity but leaves a measurable freshness gap" pattern the criteria call out explicitly, and action age reveals behavior (Q3, Q5) not explained by request latency alone. All of the "stop or reframe" conditions (e.g., "all execution strategies produce nearly identical results," "native latency is negligible relative to the execution horizon") are clearly false in this data. Recommend continuing.

## 12. What implementation or reproducibility problems remain?

Found and fixed during this phase:
- **RTC `inference_delay` was hardcoded to `0`** in every request, defeating RTC's actual guidance mechanism — fixed to use a per-episode running estimate.
- **`LEROBOT_COMMIT` floated on `main`**, causing different LeRobot code to be installed across separate deploys and producing a ~45% latency swing between otherwise-identical runs — now pinned to an exact SHA.
- **Policy action sampling was unseeded** (`torch.normal` with no `generator=` in LeRobot's flow-matching noise draw), so identical (task, seed, strategy, profile) conditions could still diverge — fixed by seeding `torch.manual_seed(seed)` per episode; residual disagreement across independent reruns dropped from ~8% to ~3% of matched conditions.
- **Five bugs in the Days 1-3 tooling itself**, found while closing this report's entry requirements: a missing `import json` and an inverted `control_frequency_hz` calculation in `profile_latency.py`; `inspect_setup.py` never actually detecting the pinned LeRobot commit (checked for a `.git` checkout that pip-installed VCS packages don't retain) and never updating its own `status` field; and four false-positive checks in `validate_results.py` (wrong queue-depth threshold, NaN vs `None` chunk-id handling, missing "ideal" profile special-case, and an off-by-one/tie-break bug in the outstanding-request-overlap check).
- **`checkpoint_revision` was `"main"`**, not a pinned SHA — the same class of risk as the `LEROBOT_COMMIT` issue above. Resolved 2026-08-06: pinned to `8e174154ef5f6c60a8da12ae99c303d8963138c1`; confirmed via the Hub commit history that no weight files changed since the initial upload, so existing Days 1-3 results did not require a rerun (see `days1_3_audit.md`, "Repository and checkpoint revisions").

Still open:
- **RTC's `execution_horizon` silently clamps** to the queue-remainder length via LeRobot's own guidance code, likely explaining the Q6 inversion at `+300ms` — not yet retuned.
- **`naive_async` and `rtc` currently share `request_threshold_actions`** — an open question on whether that's intended or should be strategy-specific.
- **No bootstrap 95% confidence intervals computed yet** (spec requirement) — n=9-15 per cell; point estimates in this report should be read with that sample size in mind, especially for cells near the residual ~3% reproducibility noise described above.
