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
n_action_steps = 10
```

No second VLA model is required for the primary result.

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
0, 100, 200, 300, 400, 500, 600, 700 ms
```

using ID only.

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

## D014 — Revised candidate action horizon after ID-only pretest

**Date:** 2026-08-12

**Decision:** Record `policy.n_action_steps=25` as the revised candidate execution
horizon after the completed `n_action_steps=10` ID calibration showed poor
success. The decision was based only on ID results; no OOD outcomes were used.

**Evidence:** On the 60 directly matched task × method × delay × seed episodes,
the 25-step configuration achieved 30/60 successes versus 8/60 for the 10-step
configuration. The gain was concentrated in RTC (22/30 versus 1/30); Naive async
was nearly unchanged (8/30 versus 7/30).

**Consequence:** Treat the 25-step bundle as a revised exploratory protocol, not
as a compliant rerun of the original Stage 0 specification. Freeze one action
horizon before Stage 1, use it unchanged across all matched ID/OOD comparisons,
and retain the post-hoc ID-based choice as a disclosed limitation. The revised
conduct is documented in `STAGE_0_N_ACTION_STEPS_25_CONDUCT.md`.

## D015 — Increase Stage 1 exploratory replication to five seeds

**Date:** 2026-08-12

**Decision:** Supersede D009's two-seed Stage 1 design with five fixed exploratory
seeds:

```text
0, 1, 2, 3, 4
```

Stage 2 held-out seeds must not overlap this set. The preferred Stage 2 set is
superseded by D017 below.

**Consequence:** Stage 1 expands to 420 OOD episodes and 60 shared ID-control
episodes, for 480 analysis episodes. Valid Stage 0 low/high controls for seeds
`0` and `1` may supply 24 ID rows; Stage 1 adds 36 ID controls for seeds `2`,
`3`, and `4`. Five seeds reduce rate granularity but Stage 1 remains exploratory.

## D016 — Freeze the revised Stage 0 calibration protocol

**Date:** 2026-08-12

**Decision:** Accept the completed ID-only Stage 0 revision using
`n_action_steps=25`, seeds `0, 1, 10, 11, 12, 13`, and added delays
`0, 100, 200, 300, 400 ms`. The originally proposed `500–700 ms` extension is
not required because the calibration supplied the needed operating-point
evidence by `400 ms`.

**Consequence:** Freeze `n_action_steps=25` and the selected `d*` before Stage 1.
Disclose that the horizon and grid were revised using ID-only evidence. Do not
describe the run as a reproduction of the original 10-action protocol.
Provenance and hold-action limitations remain reportable data-quality
limitations, but missing `500–700 ms` cells are no longer a blocker.

## D017 — Freeze disjoint Stage 1 and Stage 2 seed sets

**Date:** 2026-08-12

**Decision:** Stage 1 uses five consecutive seeds `0, 1, 2, 3, 4`. Stage 2 uses
eight consecutive seeds `14, 15, 16, 17, 18, 19, 20, 21`.

**Consequence:** Stage 2 seeds are disjoint from both Stage 1 and the six Stage 0
calibration seeds. Stage 1 may reuse valid matching Stage 0 ID controls for
seeds `0` and `1`; it must run new ID controls for seeds `2`, `3`, and `4`.

## D018 — Reuse Stage 0 seed-0/1 controls with a provenance limitation

**Date:** 2026-08-14

**Decision:** Reuse the 24 Stage 0 ID controls at Native and Native + 200 ms for
seeds `0` and `1`. Do not rerun those episodes. Stage 1 runs the 36 missing ID
controls for seeds `2`, `3`, and `4`, plus all 420 OOD episodes.

**Limitation:** The Stage 0 bundle does not contain immutable repository,
checkpoint, and environment identity fields, so exact runtime equivalence with
new Stage 1 rows cannot be proven. Imported rows must retain
`source=stage0_reuse_unverified_identity`; this limitation must accompany every
analysis that pools them with new Stage 1 episodes.

**Consequence:** Stage 1 contains 480 analysis rows but requires 456 new runs.
