# Days 1-3 Audit

Verifies the Days 1-3 harness and results against `DAYS_4_8_SPEC.md` section 2's
entry requirements, ahead of starting Days 4-8. Covers repository/checkpoint
revisions, task IDs and initial states, latency conversion, action-age
calculation, queue semantics, RTC adapter inputs, paired seeds, and missing or
invalid runs.

**Verdict: no correctness failure found that changes the scientific
conclusions in `days1_3_report.md`. One item remains an open risk worth
resolving before broad Days 4-8 experiments (see "Open items" below). The
checkpoint-pin risk flagged in the original version of this audit was
resolved 2026-08-06 without requiring a rerun (see "Repository and checkpoint
revisions"). Neither invalidates existing Days 1-3 results.**

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

1. RTC's effective `execution_horizon` is silently smaller than configured
   due to the remainder-length clamp — affects interpretation of any
   Days 4-8 RTC condition inheriting this config.
2. `naive_async` and `rtc` share `request_threshold_actions` — confirm this
   is intentional before treating them as independently-tuned baselines.
3. No bootstrap 95% CIs computed on Days 1-3 results yet.
4. The RTC adapter trace against LeRobot's source was done at `main`, not
   verified byte-for-byte at the exact pinned SHA
   (`2aba372b4e217cc47db28e0f836859b20d1456c9`) — low risk (the `sample_noise`/
   `execution_horizon`-clamp behavior is unlikely to have changed), but not
   independently confirmed at the pin.

## Resolved since this audit was written

- `checkpoint_revision: "main"` was unpinned — same risk class as the
  (already-fixed) `LEROBOT_COMMIT` issue. Resolved 2026-08-06; see
  "Repository and checkpoint revisions" above.
