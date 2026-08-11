# Decisions

All dates use local project date.

## D001 — Primary paper question

**Date:** 2026-08-09

**Decision:** Center the paper on **OOD × inference-delay interaction**.

**Consequence:** Phase-conditioned interventions and cross-model breadth are removed from the critical path.

## D002 — Primary model

**Date:** 2026-08-09

**Decision:** Use:

```text
lerobot/pi05_libero_finetuned
```

with evaluation:

```text
n_action_steps = 25
request_threshold_actions = 25
```

No second VLA model is required for the primary result.

**Amended:** 2026-08-11 — `n_action_steps` was `10`, with
`request_threshold_actions = ceil(H/2) = 5` per spec §16.

**Reason:** LIBERO runs at 20 Hz, so a chunk of `H` actions covers `H x 50 ms` of
robot time — the total request latency the action queue can absorb before it
underruns. At `H = 10` that budget is 500 ms against ~500 ms of measured native
inference (~660 ms for RTC), so the queue was starved before any artificial delay
was added. The first Stage 0 calibration held the arm on ~33-44% of control steps
at zero added delay and ~65-70% at +700 ms; all 96 of its failures were step-cap
timeouts. Its `d* = 100 ms` therefore described queue starvation, not the
policy's tolerance to stale actions. `H = 25` gives a 1250 ms budget, and the
threshold is raised to `H` because the `ceil(H/2)` default spends half that
budget draining before the request is issued.

**Consequence:** This is a change of control regime, not just of plumbing — 25
steps of open-loop execution per observation is a different condition from 10.
Days 1-3 results ran at `H = 10` (horizon sweep `[2, 5, 10]`, all further into
the same starvation regime) and are **not** directly comparable to Stage 0
onward; treat them as a separate `H = 10` condition or re-run them. Both values
apply identically to `naive_async` and `rtc`, preserving K009. Days 1-3 configs
keep the §16 default; the override is Stage 0 only.

## D003 — Execution methods

**Date:** 2026-08-09

**Decision:** The active factorial compares:

```text
Naive async
RTC
```

Historical ideal/blocking results are context only.

## D004 — Task-demand groups

**Date:** 2026-08-09

**Decision:** Use:

```text
Single-stage transport
Articulated/contact-rich
Multi-stage/sequential
```

**Consequence:** Do not use “coarse motion” as the label for the transport task.

## D005 — Perturbation coverage

**Date:** 2026-08-09

**Decision:** Screen all seven official LIBERO-Plus perturbation families rather than choosing only object layout and camera.

## D006 — Internal perturbation mechanism grouping

**Date:** 2026-08-09

**Decision:** Use:

```text
Trajectory adaptation
    Object layout
    Robot initial state

Perceptual localization
    Camera viewpoint
    Sensor noise

Appearance invariance
    Lighting
    Background texture

Semantic grounding
    Language instruction
```

**Consequence:** State explicitly that these four groups are our analysis taxonomy, not official LIBERO-Plus categories.

## D007 — Stage 0 delay grid

**Date:** 2026-08-09

**Decision:** Test added delay:

```text
0, 100, 200, 300, 400 ms
```

using ID only.

**Amended:** 2026-08-11 — the grid ran to `700 ms`.

**Reason:** The ceiling is set by RTC, not by the horizon. RTC discards the
leading `delay_steps` actions of each chunk, so its usable chunk is
`chunk_size - delay_steps` against a wait of `delay_steps`; the queue starves
once `delay_steps` exceeds half the raw chunk (25 steps / 1250 ms for pi05's
50-action chunk), at **any** `n_action_steps`. RTC's measured inference is
~660-735 ms, leaving ~500 ms of addable delay before that ceiling and ~400 ms
with margin against its p95. Levels beyond that re-measure queue starvation
rather than delay tolerance.

**Consequence:** Fallback 3 of the §8.4 selection rule now resolves to `400 ms`
rather than `700 ms`. It is implemented as `max(candidates)`, so it tracks this
grid automatically.

## D008 — Stage 1 latency levels

**Date:** 2026-08-09

**Decision:** Stage 1 uses only:

```text
Native
Native + d*
```

where `d*` is selected by the frozen Stage 0 rule.

**Consequence:** Do not tune delay against OOD outcomes or per method/task.

## D009 — Stage 1 replication

**Date:** 2026-08-09

**Decision:** Use two fixed exploratory seeds for the complete seven-family screen.

**Consequence:** Stage 1 is explicitly exploratory; it is not sufficient by itself for strong per-cell inferential claims.

## D010 — Confirmatory selection

**Date:** 2026-08-09

**Decision:** Apply a predefined eligibility/ranking rule after the full screen and use new held-out seeds for confirmation.

**Consequence:** Report the entire exploratory screen, including null results.

## D011 — Logical delay

**Date:** 2026-08-09

**Decision:** Use request-specific discrete logical time with `ceil` conversion to control steps. Never use `sleep()` to model simulated control latency.

## D012 — Variant selection

**Date:** 2026-08-09

**Decision:** For each task × perturbation family, deterministically select a moderate-difficulty LIBERO-Plus variant using `task_classification.json`; freeze the 21 resolved variants before outcomes.

## D013 — Obsolete specifications

**Date:** 2026-08-09

**Decision:** Remove the previous calendar-based Day/Week specifications from the active pack.

**Removed from active specification:**

```text
DAYS_1_3_SPEC.md
DAYS_4_8_SPEC.md
WEEK_2_SPEC.md
WEEK_3_SPEC.md
WEEK_4_SPEC.md
SPEC_VERSION_MANIFEST.md
BASELINE_COMPATIBILITY.md
EXPERIMENT_MATRIX.md
```

Their useful implementation/statistical constraints have been folded into the active files.

## D014 — Stage 0 replication

**Date:** 2026-08-11

**Decision:** Stage 0 calibration uses six seeds:

```text
0, 1, 10, 11, 12, 13
```

Seeds `0` and `1` stay first and remain the pair Stage 1 reuses for its 24 ID
controls. The extras skip `2-9`, which STAGE_2 §4 reserves as held-out
confirmatory seeds.

**Reason:** Two seeds made §8.1 viability (`Native success >= 1/2`) turn on a
single episode, since a cell's native rate could only be `0`, `0.5`, or `1.0` —
and viability determines which cells the pooled curve is computed over. Separately,
§8.3 selects the *smallest* qualifying delay, so `d*` is an order statistic:
at six episodes per pooled point the standard error is ~20 points, the same size
as the 20-point drop criterion, which biases `d*` downward rather than merely
scattering it. Six seeds give 18 episodes per point and ~11 points of error.

**Consequence:** D009 is unchanged — Stage 1 remains a two-seed exploratory
screen, and Stage 2 remains the confirmatory stage. This decision applies to
Stage 0 only, where `d*` is a single frozen parameter that 168 Stage 1 and
~96-128 Stage 2 episodes inherit and that no amount of held-out replication can
repair after the fact. Stage 0 grows from 96 to 180 episodes.
