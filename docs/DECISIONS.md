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

**Status:** The seed values remain frozen but their stage label is superseded by
D025: seeds `14..21` now belong to Stage 3 held-out confirmation, while Stage 2
local sensitivity uses seeds `5..9`.

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


## D019 — Stage 1 broad OOD interaction is treated as near-null

**Date:** 2026-08-16

**Decision:** Do not claim broad OOD amplification of +200 ms delay.

**Evidence:** `I ≈ +1.4 pp` pooled.

**Consequence:** Preserve the full null result and pivot the next experiment to
the stronger horizon-dependence signal.

## D020 — Initial full horizon × latency phase diagram plan (superseded)

**Date:** 2026-08-16

**Decision:** Run RTC on ID across:

```text
n_action_steps = 10,15,20,25
added delay = 0,100,200,300,400,500,600,700 ms
```

with a sparse Naive control.

**Rationale:** RTC theory explicitly couples inference delay and execution
horizon, and project results differ sharply between 10 and 25 actions.

**Status:** Superseded first by D026's 270-episode local sensitivity proposal and
then by D028's active 360-episode matrix with same-seed Native baselines. Retained
here as decision history; do not execute the original full grid.

## D021 — Preserve Stage 1 family tie; sensor noise remains post-hoc

**Date:** 2026-08-16

**Decision:** Stage 3 confirmatory families are Object layout, Robot initial
state, and Lighting. Sensor noise is a separate post-hoc replication.

## D022 — OOD follow-up spans horizons

**Date:** 2026-08-16

**Decision:** Stage 3 uses `n_action_steps = 10,15,25`, Native/+200 ms, RTC, and
held-out seeds 14..21.

**Status:** The fixed `{10,15,25}` horizon choice is superseded by D027. Stage 3
still spans three horizons, but the two values below 25 are selected from Stage 2
ID-only results, with `{10,20,25}` as the documented fallback.

## D023 — VLASH is conditional external validation

**Date:** 2026-08-16

**Decision:** Add a compact VLASH subset only after Stages 2 and 3 and only if
official code passes a strict π0.5/LIBERO compatibility gate.

**Consequence:** SmolVLA remains outside the critical path.

## D024 — Do not equate `n_action_steps` with RTC formal horizon without audit

**Date:** 2026-08-16

**Decision:** Use the term **configured action coverage (`n_action_steps`)** until
implementation inspection proves equivalence to RTC execution horizon `s`.


## D025 — Fixed post-Stage-1 seed allocation

**Date:** 2026-08-16

**Decision:**

```text
Stage 2 local sensitivity: [5,6,7,8,9]
Stage 3 held-out confirmation: [14,15,16,17,18,19,20,21]
Stage 4 conditional VLASH: [22,23,24,25,26]
```

**Rationale:** These are disjoint from completed Stage 1 `[0..4]` and from the
revised Stage 0 additional seeds `[10..13]`.

**Consequence:** Use the same seed set in every condition within a stage. Invalid
episodes are rerun with the same seed rather than replaced with a new seed.

## D026 — Stage 2 is local sensitivity, not global horizon optimization (superseded matrix)

**Date:** 2026-08-16

**Decision:** Run:

```text
n_action_steps = 10,15,20,25,30,35
added delay = 100,200,300 ms
RTC
seeds = 5..9
```

**Rationale:** 25/+200 is the frozen Stage 1 operating point. The experiment
tests symmetric local perturbations plus the known 10-action brittle anchor.

**Consequence:** Stage 2 does not redefine Stage 1's configuration even if another
cell performs better.

**Status:** The scientific purpose and six-horizon set remain active, but this
three-delay, 270-episode matrix is superseded by D028. The required Stage 2
matrix includes Native at every horizon and contains 360 episodes. This entry is
retained as provenance for the earlier proposal; do not execute it.

## D027 — Stage 3 horizons selected from ID-only Stage 2

**Date:** 2026-08-16

**Decision:** Stage 3 uses three horizons:
- one lower degraded regime;
- one intermediate regime;
- 25-action Stage 1 reference.

The first two are selected only from Stage 2 ID results before any new Stage 3 OOD
outcomes.

**Fallback:** `{10,20,25}` if Stage 2 does not distinguish a transition.

**Consequence:** Do not hard-code `{10,15,25}` and do not use 30/35 to
retrospectively replace Stage 1's reference point.


## D028 — Add same-seed Native baselines to Stage 2

**Date:** 2026-08-16

**Decision:** Supersede D026's 270-episode matrix with:

```text
RTC
n_action_steps = 10,15,20,25,30,35
delay = Native,100,200,300 ms
tasks = 3 ID tasks
seeds = 5,6,7,8,9
total = 360 episodes
```

**Rationale:** Native performance must be measured at every tested
`n_action_steps` under the same Stage 2 seeds. Otherwise an intrinsically weak
horizon can be mistaken for delay sensitivity.

**Consequence:** Stage 2 separately reports each horizon's Native baseline and the
success drop from Native at +100/+200/+300 ms. Stage 0 and Stage 1 remain unchanged.

## D029 — Freeze Stage 3 horizons before Stage 2

**Date:** 2026-08-16

**Decision:** Supersede D027's adaptive horizon-selection rule. Stage 3 uses:

```text
n_action_steps = 20,25,30
```

**Rationale:** These are a symmetric ±5-action neighborhood around the exact
Stage 1 reference at 25 actions. Choosing lower/transition horizons after viewing
Stage 2 would introduce avoidable analyst discretion and could bias the OOD
follow-up.

**Consequence:** Do not replace 20 or 30 after Stage 2 even if another horizon
performs better. Stage 2 is sensitivity analysis, not Stage 3 condition selection.


## D030 — Replicate conditions, not completed episode seeds

**Date:** 2026-08-16

**Decision:** New stages use disjoint seed blocks rather than recycling completed
Stage 0/1 episode seeds.

```text
Stage 2: 5..9
Stage 3: 14..21
Stage 4: 22..26
```

**Rationale:** This gives independent replication while preserving comparability.

**Consequence:** Matching is strict within each new stage. For a fixed
task/variant/seed, horizon and delay comparisons must share the same initialization
identity.

## D031 — Freeze exact Stage 1 OOD variant identities for Stage 3

**Date:** 2026-08-16

**Decision:** The Stage 3 OOD follow-ups use these exact Stage 1 variants:

| Follow-up status | Task | Perturbation | `classification_id` | `api_task_index` | Exact Stage 1 `variant_name` |
|---|---|---|---:|---:|---|
| Prespecified confirmatory | `long_stove_moka` | `object_layout` | `1941` | `1940` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25` |
| Prespecified confirmatory | `goal_drawer` | `robot_initial_state` | `285` | `284` | `open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_71` |
| Prespecified confirmatory | `goal_drawer` | `light_conditions` | `2313` | `2312` | `open_the_middle_drawer_of_the_cabinet_light_1` |
| Secondary post-hoc replication | `goal_drawer` | `sensor_noise` | `1509` | `1508` | `open_the_middle_drawer_of_the_cabinet_view_0_0_100_0_0_initstate_0_noise_1` |

**Consequence:** `classification_id`, `api_task_index`, `variant_name`, and
difficulty level are immutable experimental fields. Do not select another variant
from the same family.

## D032 — Seed equality is not sufficient evidence of episode matching

**Date:** 2026-08-16

**Decision:** Future manifests record an explicit initialization index/ID or stable
reset-state fingerprint.

**Rationale:** A seed may control multiple sources of randomness and does not by
itself prove that two runs began from the same simulator state.

**Consequence:** Validate episode pairing before using paired statistical analyses.
