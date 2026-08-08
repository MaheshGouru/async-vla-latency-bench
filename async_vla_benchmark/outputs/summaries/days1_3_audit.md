# Days 1-3 Audit

Verifies the Days 1-3 harness and results against `DAYS_4_8_SPEC.md` section 2's
entry requirements, ahead of starting Days 4-8. Covers repository/checkpoint
revisions, task IDs and initial states, latency conversion, action-age
calculation, queue semantics, RTC adapter inputs, paired seeds, and missing or
invalid runs.

**Verdict (revised 2026-08-08): both correctness failures are fixed and the full
re-run has landed. Entry requirements are met.**

The two defects found on 2026-08-07 — RTC guidance never active, and
`request_threshold_actions` set to `8` rather than the `5` that spec section 15
specifies — were corrected and all 222 episodes re-executed on 2026-08-08
(A100-40GB, LeRobot `2aba372b`, checkpoint `8e174154`). `validate_results.py`
reports 0 errors with the RTC checks *firing* rather than skipping: all 1477 RTC
requests carry `rtc_*` diagnostics and all 3998 requests are CUDA-synchronized.
`days1_3_report.md` has been rewritten against this data; every pre-2026-08-07
`naive_async` and `rtc` result is withdrawn.

A third defect was found and fixed during the re-run itself: `prev_chunk_left_over`
was passed to LeRobot as a numpy array, which crashed `RTCProcessor.denoise_step`
on the first RTC episode. It had been invisible because the argument was
previously discarded unread (see `UPSTREAM_CHANGES.md` items 1 and 2).

**Two findings carry into Days 4-8 and should be settled before broad experiments:**

1. **RTC contributes zero guided actions** at every horizon in the spec matrix
   (0 across all 81 episodes, h=2/5/10). Native inference occupies 11 control
   steps against a 10-step horizon, so `inference_delay ≥ effective_horizon` and
   guidance cannot reach an executed action. Any Days 4-8 RTC condition
   inheriting `policy_n_action_steps: 10` will reproduce this null.
2. **Native inference occupies the whole execution horizon.** The section 7
   profile measures 476.8 ms p50, which is 10 control steps at 20 Hz against a
   configured horizon of 10 (13 steps with RTC guidance enabled). Inference
   speed itself is stable — the 2026-08-06 and 2026-08-08 dedicated profiles
   agree to +3.6% — so this is a property of the experimental design, not drift.
   Any Days 4-8 condition at `policy_n_action_steps: 10` inherits it.

*Superseded verdicts, retained for provenance:* the 2026-08-07 verdict above, and
the original "no correctness failure found that changes the scientific
conclusions... Neither invalidates existing Days 1-3 results." The latter rested
on the assumption that RTC guidance was running, which was never verified against
the installed policy at the time.

*Superseded verdict, retained for provenance:* "no correctness failure found
that changes the scientific conclusions... Neither invalidates existing Days 1-3
results." That conclusion rested on the assumption that RTC guidance was
running, which was never verified against the installed policy at the time.
The checkpoint-pin risk it describes was genuinely resolved 2026-08-06 and did
not require a re-run (see "Repository and checkpoint revisions").

---

## Repository and checkpoint revisions

- **LeRobot commit**: pinned to `2aba372b4e217cc47db28e0f836859b20d1456c9`
  (`modal_app.py`'s `LEROOT_COMMIT`), confirmed installed via
  `environment.json`'s `lerobot_git_commit` field on the container that
  produced the current dataset.
  - **Before this was pinned**, `LEROBOT_COMMIT` floated on `main`, and two
    otherwise-identical runs measured native latency ~48% apart (see
    `days1_3_report.md` section 12). All results referenced in the current
    report were generated after pinning.
- **Checkpoint revision**: **Resolved 2026-08-06.** `checkpoint_revision` in
  `days1_3.yaml` was `"main"` (unpinned) at the time this audit was originally
  written — the same class of risk the LeRobot commit issue turned out to be.
  Pinned to `8e174154ef5f6c60a8da12ae99c303d8963138c1` after checking the Hub
  commit history for `lerobot/pi05_libero_finetuned`: every commit after the
  initial weights upload (`6348c67dbb...`, 2025-10-01) only touched the
  README, including the commit that was current `main` on 2026-08-06
  (`8e17415...`, "Add link to paper (#1)"). No weight files have changed
  since the initial upload, so whatever `main` resolved to during the actual
  Days 1-3 runs, it was the same weights as this pin — no rerun required.
  `inspect_setup.py` now loads the config and resolves `checkpoint_revision`
  against the Hub API into `checkpoint_revision_sha`, so this is
  independently re-verified on every future run rather than trusted from the
  config alone. Confirmed on a real Modal/A100 run (2026-08-06):
  `environment.json` recorded
  `checkpoint_revision_sha: "8e174154ef5f6c60a8da12ae99c303d8963138c1"` with
  `status: "ready"` and zero deviations.
- **Dataset revision**: `dataset_revision: null` in config; not used for
  training in this project (spec's own framing — the dataset only defines
  preprocessing/normalization conventions), and no discrepancy attributable to
  it was found.

## Task IDs and initial states

- Selected tasks: `libero_spatial:0`, `libero_goal:0`, `libero_10:0` — one per
  suite, each selected via 5 `ideal_sync` pilot episodes achieving ≥4/5
  success, recorded in `task_selection.csv`/`selected_tasks.json`.
- `env.reset(seed=X)` is deterministic for initial state (verified: identical
  seeds produce identical initial observations across separate runs — the
  divergence found during reproducibility investigation, see "paired seeds"
  below, occurs *after* reset, in policy action generation, not at
  initialization).

## Latency conversion

- `latency_to_delay_steps` uses `ceil()`, not `round()`, matching spec
  section 8. Verified directly: `native_latency.json`'s p50/p95/p99 (460.1 /
  467.2 / 469.9 ms) at 50ms control period all convert to exactly 10 steps
  via `ceil()`.
- The `"ideal"` latency profile forces `delay_steps=0` regardless of measured
  request latency (spec section 8/12) — confirmed both in code
  (`LatencyProfile.logical_latency_ms`) and in data (every `ideal_sync`/
  `"ideal"`-profile request has `delay_steps=0` despite `measured_request_latency_ms`
  in the 360-470ms range).
- `validate_results.py`'s delay-conversion check (`_check_delay_conversion`)
  did not originally special-case the `"ideal"` profile, producing 72 false
  failures against exactly this expected zero-delay behavior. Fixed during
  this audit; all 222 episodes now validate cleanly against the `ceil()`
  conversion.

## Action-age calculation

- `action_age_steps = execution_control_step - source_observation_step`,
  computed from provenance (not inference completion time), matching spec
  section 10. Verified via `_record_action` in `execution.py`.
- Cross-checked against aggregate data: `mean_action_age_ms` for async
  strategies (585-602ms) exceeds `mean_request_latency_ms` (~400ms) by a
  consistent ~1.4-1.5x ratio (`days1_3_report.md` Q3) — the expected
  direction and magnitude for actions executed throughout a buffered chunk
  rather than only at response arrival.

## Queue semantics

- One outstanding request enforced at runtime by
  `ActionQueue.begin_request()`'s `RuntimeError` guard — never triggered
  across 222 executed episodes (would have crashed the episode, and none
  did).
- `validate_results.py`'s independent overlap check
  (`_check_outstanding_overlap`) initially had two bugs producing false
  positives on every episode: an incorrectly-initialized counter (`active = 1`
  instead of `0`) and an off-by-one in the resolved-request boundary
  (`response_available_step + 1` instead of `response_available_step`,
  combined with a tie-break sort order that processed a new request's start
  before a same-step response's resolution). Both fixed during this audit,
  matching the runtime's actual resolve-then-request order within one
  control step (`EpisodeRunner.run()`'s loop calls `_take_available()` before
  `_maybe_request()` each iteration).
- `discarded_old_actions` is `0` across every episode in the dataset — not a
  bug: given `request_threshold_actions=8` (out of `horizon=10`) and native
  request latency occupying the full 10-step horizon (Q2), the queue is
  reliably empty by the time a replacement chunk arrives, so there is
  nothing left to discard. Confirmed by direct queue-depth timeline
  inspection during this project (a `naive_async`/`horizon=2` episode showed
  81.3% of all control steps as hold steps).

## RTC adapter inputs

> **CORRECTION (2026-08-07): RTC guidance was never active in any Days 1-3 run.**
> The findings in this section were written on the assumption that guidance was
> running and only its inputs were in question. That assumption is wrong, and the
> analysis below is superseded.
>
> `configure_rtc()` existed in `benchmark/rtc.py` from the initial commit but was
> **never called** — `git log -S configure_rtc` returns only `07f9007`, and
> `git grep configure_rtc HEAD` finds no caller outside `rtc.py` itself.
> `load_pi05_policy` never touches `config.rtc_config`, so it kept the `None` that
> `PI05Config` defaults to and that the `pi05_libero_finetuned` checkpoint ships.
>
> Confirmed empirically on Modal/A100 against the pinned LeRobot
> (`2aba372b4e217cc47db28e0f836859b20d1456c9`) via
> `scripts/diagnose_rtc.py`, 2026-08-07:
>
> ```text
> === AS THE DAYS 1-3 RUNS LOADED IT (pre-fix behavior) ===
>   config.rtc_config:      None
>   policy.rtc_processor:   None
>   policy._rtc_enabled():  false
>
> === AFTER configure_rtc (post-fix behavior) ===
>   config.rtc_config:      RTCConfig(enabled=True,
>                             prefix_attention_schedule=RTCAttentionSchedule.EXP,
>                             max_guidance_weight=10.0, execution_horizon=10, ...)
>   policy.rtc_processor:   <lerobot.policies.rtc.modeling_rtc.RTCProcessor object>
>   policy._rtc_enabled():  true
>
> === VERDICT ===
> Days 1-3 runs had RTC guidance active: False
> configure_rtc activates guidance:      True
> ```
>
> Consequences:
>
> - All 81 `rtc` episodes in the shipped dataset are invalid as RTC. They ran as
>   `naive_async` plus the delay-aligned chunk truncation in `execution.py`
>   (`raw_chunk[delay_steps:]`), which is what produced the 93.3% vs 33.3% result
>   at native latency — not guidance.
> - The "open risk" below (LeRobot clamping `execution_horizon` to the remainder
>   length) describes code inside the guidance path, which never executed. It
>   cannot be the cause of the `native+300` inversion reported in
>   `days1_3_report.md` Q6, and that answer needs rewriting rather than re-running.
> - Independently of the activation bug, `discarded_old_actions = 0` in all 222
>   episodes proves the queue was empty at every chunk replacement. Since the
>   actions RTC would guide are exactly the actions `naive_async` discards
>   (`guided = max(0, threshold - delay_steps)`), guidance had nothing to act on
>   even had it been enabled.
> - A second, independent defect compounds this: `request_threshold_actions` was
>   `8`, not the `ceil(fixed_horizon / 2)` that spec sections 14, 15, and 16 all
>   require. That invalidates the 81 `naive_async` episodes as well, for reasons
>   unrelated to RTC.
>
> The 45 `blocking_sync` and 15 `ideal_sync` episodes are unaffected by both
> defects: neither strategy calls `should_request()`, so neither ever saw the
> threshold, and neither uses RTC. Re-run of the 162 affected episodes was
> dispatched 2026-08-07.


- **Fixed during this project**: `inference_delay` was hardcoded to `0` on
  every RTC request (`execution.py`, prior to fix), meaning RTC's guidance
  was computed as if every response arrived instantaneously, regardless of
  the actual latency profile. This was a genuine defect against spec section
  15's explicit requirement ("The runtime `inference_delay` must use the
  current request's measured latency"). Fixed to use a per-episode running
  estimate of prior request latency (the current request's own latency isn't
  knowable before it completes).
- `prev_chunk_left_over` (the queue remainder at request time) and
  `execution_horizon` are passed through correctly — verified against
  `test_rtc.py` and by tracing `rtc.py`'s adapter against LeRobot's actual
  installed `modeling_rtc.py`/`action_queue.py` source (fetched at the pinned
  commit's `main`-branch equivalent; not verified at the exact pinned SHA —
  see open items).
- **Open risk, not yet resolved**: LeRobot's own guidance code clamps
  `execution_horizon` down to `len(prev_chunk_left_over)` when the queue
  remainder is shorter than the configured horizon — under
  `request_threshold_actions=8`, the remainder is reliably ≤8, so RTC's
  effective `execution_horizon` is silently smaller than the `10` configured
  in `days1_3.yaml`. Plausible explanation for RTC underperforming
  `naive_async` at `native+300ms` (`days1_3_report.md` Q6) — not yet
  confirmed as the sole cause, not yet retuned.

## Paired seeds

- Core experiment uses seeds `[0,1,2,3,4]` per condition; horizon sweep uses
  `[0,1,2]`, matching spec sections 18/16.
- **Reproducibility investigated directly**: rerunning the same nominal
  (task, strategy, profile, horizon, seed) condition in two independent
  executions initially showed 2-3 of 36 shared conditions (5.6-8.3%)
  disagreeing on pass/fail, traced to LeRobot's flow-matching noise sampling
  drawing from PyTorch's unseeded global RNG
  (`lerobot.policies.common.flow_matching.sample_noise`, confirmed by
  reading the installed source directly). Fixed by seeding
  `torch.manual_seed(seed)` per episode in `EpisodeRunner.run()`; residual
  disagreement after the fix dropped to 1/36 (2.8%).
- **This residual (~3%) is not eliminated** — likely GPU/cuDNN floating-point
  non-determinism independent of RNG seeding. `days1_3_report.md`'s
  per-condition success rates at n=9-15 should be read as having this much
  inherent noise; no bootstrap CIs are computed yet to quantify it formally
  (open item, tracked in the report).

## Missing or invalid runs

- 222 unique executed episodes (150 core + 72 horizon-sweep-only, since 36
  `horizon_sweep` `h=10` conditions are shared with `core` and reused rather
  than re-executed) — all present, all pass `validate_results.py` (exit code
  0, 0 errors).
- No missing `episodes/`, `requests/`, or `actions/` files for any of the 222
  (one transient download gap found and closed during this audit — a local
  copy of `actions/libero_spatial_tid0_rtc_native_plus_700_h2_s2.parquet` was
  missing from an earlier bulk download despite it existing correctly on the
  volume; re-downloaded and confirmed).
- Full raw per-episode data now aggregated into
  `summaries/{episodes,requests,horizon_sweep}.csv` for this audit and for
  Days 4-8 use.

---

## Open items (not blocking, but should be resolved before broad Days 4-8 experiments)

1. **RESOLVED (measured).** RTC's effective `execution_horizon` is clamped to the
   remainder length: **4.67** against a configured **10**, now recorded per
   request as `rtc_effective_execution_horizon`. The clamp is real; it is no
   longer a hidden quantity.
2. **RESOLVED (intentional).** `naive_async` and `rtc` share
   `request_threshold_actions` by spec section 16: "Use the same horizon and
   threshold for paired `naive_async` and RTC runs."
3. **RESOLVED.** Wilson 95% intervals are reported for success rates
   (`days1_3_report.md` question 6); they are wide at n=15 and overlap for most
   pairwise comparisons, so conclusions there rest on mechanism rather than
   rates. Bootstrap 95% intervals (10000 resamples, n=45) are reported for the
   continuous metrics in question 7; all three continuity intervals exclude zero
   (delta −29.1% [−39.6, −16.8], acceleration −22.5% [−34.2, −8.5], jerk −23.6%
   [−34.6, −10.2]).
4. **RESOLVED.** The section 7 profiling pass was re-run 2026-08-08 (10 warmup +
   100 measured, CUDA-synchronized): p50 476.8 / p95 489.9 / p99 499.8 ms,
   std 6.6 ms. The CUDA event time matches the wall-clock model time to 0.1 ms,
   confirming synchronization. `native_latency.json` and `native_latency.csv` on
   the volume are current.

   *Left open:* the superseded 2026-08-06 run recorded ~400 ms in-run against
   its own 460 ms profile — 13% below a figure that should be a lower bound. The
   cause was never identified. It affects no result reported now, but it is a
   reason to distrust pre-2026-08-07 latency numbers specifically.
5. **NEW: 87-98% of async episodes end by timeout** rather than task outcome, so
   success rates partly measure "finished within the step cap".
4. The RTC adapter trace against LeRobot's source was done at `main`, not
   verified byte-for-byte at the exact pinned SHA
   (`2aba372b4e217cc47db28e0f836859b20d1456c9`) — low risk (the `sample_noise`/
   `execution_horizon`-clamp behavior is unlikely to have changed), but not
   independently confirmed at the pin.

## Resolved since this audit was written

- `checkpoint_revision: "main"` was unpinned — same risk class as the
  (already-fixed) `LEROBOT_COMMIT` issue. Resolved 2026-08-06; see
  "Repository and checkpoint revisions" above.
