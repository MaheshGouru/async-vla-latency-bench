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
