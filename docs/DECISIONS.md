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

## D007 — Latency Calibration and Instrumentation delay grid

**Date:** 2026-08-09

**Decision:** Test added delay:

```text
0, 100, 200, 300, 400, 500, 600, 700 ms
```

using ID only.

## D008 — Exploratory OOD–Delay Screening latency levels

**Date:** 2026-08-09

**Decision:** Exploratory OOD–Delay Screening uses only:

```text
Native
Native + d*
```

where `d*` is selected by the frozen Latency Calibration and Instrumentation rule.

**Consequence:** Do not tune delay against OOD outcomes or per method/task.

## D009 — Exploratory OOD–Delay Screening replication

**Date:** 2026-08-09

**Decision:** Use two fixed exploratory seeds for the complete seven-family screen.

**Consequence:** Exploratory OOD–Delay Screening is explicitly exploratory; it is not sufficient by itself for strong per-cell inferential claims.

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
as a compliant rerun of the original Latency Calibration and Instrumentation specification. Freeze one action
horizon before Exploratory OOD–Delay Screening, use it unchanged across all matched ID/OOD comparisons,
and retain the post-hoc ID-based choice as a disclosed limitation. The revised
conduct is documented in `STAGE_0_N_ACTION_STEPS_25_CONDUCT.md`.

## D015 — Increase Exploratory OOD–Delay Screening exploratory replication to five seeds

**Date:** 2026-08-12

**Decision:** Supersede D009's two-seed Exploratory OOD–Delay Screening design with five fixed exploratory
seeds:

```text
0, 1, 2, 3, 4
```

Confirmatory Horizon–Delay Operating Envelope held-out seeds must not overlap this set. The preferred Confirmatory Horizon–Delay Operating Envelope set is
superseded by D017 below.

**Consequence:** Exploratory OOD–Delay Screening expands to 420 OOD episodes and 60 shared ID-control
episodes, for 480 analysis episodes. Valid Latency Calibration and Instrumentation low/high controls for seeds
`0` and `1` may supply 24 ID rows; Exploratory OOD–Delay Screening adds 36 ID controls for seeds `2`,
`3`, and `4`. Five seeds reduce rate granularity but Exploratory OOD–Delay Screening remains exploratory.

## D016 — Freeze the revised Latency Calibration and Instrumentation calibration protocol

**Date:** 2026-08-12

**Decision:** Accept the completed ID-only Latency Calibration and Instrumentation revision using
`n_action_steps=25`, seeds `0, 1, 10, 11, 12, 13`, and added delays
`0, 100, 200, 300, 400 ms`. The originally proposed `500–700 ms` extension is
not required because the calibration supplied the needed operating-point
evidence by `400 ms`.

**Consequence:** Freeze `n_action_steps=25` and the selected `d*` before Exploratory OOD–Delay Screening.
Disclose that the horizon and grid were revised using ID-only evidence. Do not
describe the run as a reproduction of the original 10-action protocol.
Provenance and hold-action limitations remain reportable data-quality
limitations, but missing `500–700 ms` cells are no longer a blocker.

## D017 — Freeze disjoint Exploratory OOD–Delay Screening and Confirmatory Horizon–Delay Operating Envelope seed sets

**Date:** 2026-08-12

**Decision:** Exploratory OOD–Delay Screening uses five consecutive seeds `0, 1, 2, 3, 4`. Confirmatory Horizon–Delay Operating Envelope uses
eight consecutive seeds `14, 15, 16, 17, 18, 19, 20, 21`.

**Consequence:** Confirmatory Horizon–Delay Operating Envelope seeds are disjoint from both Exploratory OOD–Delay Screening and the six Latency Calibration and Instrumentation
calibration seeds. Exploratory OOD–Delay Screening may reuse valid matching Latency Calibration and Instrumentation ID controls for
seeds `0` and `1`; it must run new ID controls for seeds `2`, `3`, and `4`.

**Status:** The seed values remain frozen but their stage label is superseded by
D025: seeds `14..21` now belong to Held-Out OOD–Delay Horizon Confirmation, while Confirmatory Horizon–Delay Operating Envelope
local sensitivity uses seeds `5..9`.

## D018 — Reuse Latency Calibration and Instrumentation seed-0/1 controls with a provenance limitation

**Date:** 2026-08-14

**Decision:** Reuse the 24 Latency Calibration and Instrumentation ID controls at Native and Native + 200 ms for
seeds `0` and `1`. Do not rerun those episodes. Exploratory OOD–Delay Screening runs the 36 missing ID
controls for seeds `2`, `3`, and `4`, plus all 420 OOD episodes.

**Limitation:** The Latency Calibration and Instrumentation bundle does not contain immutable repository,
checkpoint, and environment identity fields, so exact runtime equivalence with
new Exploratory OOD–Delay Screening rows cannot be proven. Imported rows must retain
`source=stage0_reuse_unverified_identity`; this limitation must accompany every
analysis that pools them with new Exploratory OOD–Delay Screening episodes.

**Consequence:** Exploratory OOD–Delay Screening contains 480 analysis rows but requires 456 new runs.


## D019 — Exploratory OOD–Delay Screening broad OOD interaction is treated as near-null

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

## D021 — Preserve Exploratory OOD–Delay Screening family tie; sensor noise remains post-hoc

**Date:** 2026-08-16

**Decision:** Held-Out OOD–Delay Horizon Confirmation confirmatory families are Object layout, Robot initial
state, and Lighting. Sensor noise is a separate post-hoc replication.

## D022 — OOD follow-up spans horizons

**Date:** 2026-08-16

**Decision:** Held-Out OOD–Delay Horizon Confirmation uses `n_action_steps = 10,15,25`, Native/+200 ms, RTC, and
held-out seeds 14..21.

**Status:** The fixed `{10,15,25}` horizon choice is superseded by D027. Held-Out OOD–Delay Horizon Confirmation
still spans three horizons, but the two values below 25 are selected from Confirmatory Horizon–Delay Operating Envelope
ID-only results, with `{10,20,25}` as the documented fallback.

## D024 — Do not equate `n_action_steps` with RTC formal horizon without audit

**Date:** 2026-08-16

**Decision:** Use the term **configured action coverage (`n_action_steps`)** until
implementation inspection proves equivalence to RTC execution horizon `s`.


## D025 — Fixed post-Exploratory OOD–Delay Screening seed allocation

**Date:** 2026-08-16

**Decision:**

```text
Confirmatory Horizon–Delay Operating Envelope local sensitivity: [5,6,7,8,9]
Held-Out OOD–Delay Horizon Confirmation: [14,15,16,17,18,19,20,21]
```

**Rationale:** These are disjoint from completed Exploratory OOD–Delay Screening `[0..4]` and from the
revised Latency Calibration and Instrumentation additional seeds `[10..13]`.

**Consequence:** Use the same seed set in every condition within a stage. Invalid
episodes are rerun with the same seed rather than replaced with a new seed.

## D026 — Confirmatory Horizon–Delay Operating Envelope is local sensitivity, not global horizon optimization (superseded matrix)

**Date:** 2026-08-16

**Decision:** Run:

```text
n_action_steps = 10,15,20,25,30,35
added delay = 100,200,300 ms
RTC
seeds = 5..9
```

**Rationale:** 25/+200 is the frozen Exploratory OOD–Delay Screening operating point. The experiment
tests symmetric local perturbations plus the known 10-action brittle anchor.

**Consequence:** Confirmatory Horizon–Delay Operating Envelope does not redefine Exploratory OOD–Delay Screening's configuration even if another
cell performs better.

**Status:** The scientific purpose and six-horizon set remain active, but this
three-delay, 270-episode matrix is superseded by D028. The required Confirmatory Horizon–Delay Operating Envelope
matrix includes Native at every horizon and contains 360 episodes. This entry is
retained as provenance for the earlier proposal; do not execute it.

## D027 — Held-Out OOD–Delay Horizon Confirmation horizons selected from ID-only Confirmatory Horizon–Delay Operating Envelope

**Date:** 2026-08-16

**Decision:** Held-Out OOD–Delay Horizon Confirmation uses three horizons:
- one lower degraded regime;
- one intermediate regime;
- 25-action Exploratory OOD–Delay Screening reference.

The first two are selected only from Confirmatory Horizon–Delay Operating Envelope ID results before any new Held-Out OOD–Delay Horizon Confirmation OOD
outcomes.

**Fallback:** `{10,20,25}` if Confirmatory Horizon–Delay Operating Envelope does not distinguish a transition.

**Consequence:** Do not hard-code `{10,15,25}` and do not use 30/35 to
retrospectively replace Exploratory OOD–Delay Screening's reference point.


## D028 — Add same-seed Native baselines to Confirmatory Horizon–Delay Operating Envelope

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
`n_action_steps` under the same Confirmatory Horizon–Delay Operating Envelope seeds. Otherwise an intrinsically weak
horizon can be mistaken for delay sensitivity.

**Consequence:** Confirmatory Horizon–Delay Operating Envelope separately reports each horizon's Native baseline and the
success drop from Native at +100/+200/+300 ms. Latency Calibration and Instrumentation and Exploratory OOD–Delay Screening remain unchanged.

## D029 — Freeze Held-Out OOD–Delay Horizon Confirmation horizons before Confirmatory Horizon–Delay Operating Envelope

**Date:** 2026-08-16

**Decision:** Supersede D027's adaptive horizon-selection rule. Held-Out OOD–Delay Horizon Confirmation uses:

```text
n_action_steps = 20,25,30
```

**Rationale:** These are a symmetric ±5-action neighborhood around the exact
Exploratory OOD–Delay Screening reference at 25 actions. Choosing lower/transition horizons after viewing
Confirmatory Horizon–Delay Operating Envelope would introduce avoidable analyst discretion and could bias the OOD
follow-up.

**Consequence:** Do not replace 20 or 30 after Confirmatory Horizon–Delay Operating Envelope even if another horizon
performs better. Confirmatory Horizon–Delay Operating Envelope is sensitivity analysis, not Held-Out OOD–Delay Horizon Confirmation condition selection.


## D030 — Replicate conditions, not completed episode seeds

**Date:** 2026-08-16

**Decision:** New stages use disjoint seed blocks rather than recycling completed
Latency Calibration and Instrumentation/1 episode seeds.

```text
Confirmatory Horizon–Delay Operating Envelope: 5..9
Held-Out OOD–Delay Horizon Confirmation: 14..21
```

**Rationale:** This gives independent replication while preserving comparability.

**Consequence:** Matching is strict within each new stage. For a fixed
task/variant/seed, horizon and delay comparisons must share the same initialization
identity.

## D031 — Freeze exact Exploratory OOD–Delay Screening OOD variant identities for Held-Out OOD–Delay Horizon Confirmation

**Date:** 2026-08-16

**Decision:** The Held-Out OOD–Delay Horizon Confirmation OOD follow-ups use these exact Exploratory OOD–Delay Screening variants:

| Follow-up status | Task | Perturbation | `classification_id` | `api_task_index` | Exact Exploratory OOD–Delay Screening `variant_name` |
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


## D033 — Add targeted Held-Out Object-Layout Cross-Task Replication

**Date:** 2026-08-16

**Decision:** After the completed Held-Out OOD–Delay Horizon Confirmation analysis, add a narrow
Held-Out Object-Layout Cross-Task Replication testing the already-frozen Exploratory OOD–Delay Screening object-layout variants on the two remaining
pre-existing benchmark tasks: `spatial_transport` and `goal_drawer`.

**Rationale:** The completed Held-Out OOD–Delay Horizon Confirmation object-layout result on `long_stove_moka` had
a negative OOD × delay interaction with the same direction at horizons 20, 25,
and 30, while the other Held-Out OOD–Delay Horizon Confirmation perturbations did not provide a comparable
negative replication. A family-level object-layout claim therefore requires
cross-task evidence rather than extrapolation from one task.

**Frozen Held-Out Object-Layout Cross-Task Replication configuration:**

```text
method = RTC
tasks = spatial_transport, goal_drawer
perturbation = object_layout
n_action_steps = 20,25,30
delay = Native,+200 ms
seeds = 14..21
initialization_index_or_id = libero_episode_index:0
```

Exact OOD identities:

```text
spatial_transport: classification_id=1773, api_task_index=1772, difficulty=3,
  variant=pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15
goal_drawer: classification_id=1891, api_task_index=1890, difficulty=2,
  variant=open_the_middle_drawer_of_the_cabinet_add_13
```

**Control reuse:** Reuse the 48 valid Held-Out OOD–Delay Horizon Confirmation `goal_drawer` ID rows exactly. Run
48 new `spatial_transport` ID rows because Held-Out OOD–Delay Horizon Confirmation contains no spatial ID control.
Run 96 new OOD rows. Total new Held-Out Object-Layout Cross-Task Replication execution is **144 episodes**. No new
`long_stove_moka` episodes are run.

**Interpretation:** Held-Out Object-Layout Cross-Task Replication is explicitly a post-Held-Out OOD–Delay Horizon Confirmation targeted cross-task
replication, not preregistered confirmation and not an independent new-seed replication.


## D3C01 — Held-Out Object-Layout Cross-Task Replication is completed; do not reuse its label

**Date:** 2026-08-16

**Decision:** Held-Out Object-Layout Cross-Task Replication is treated as completed targeted cross-task object-layout
replication. All newly added work begins at Initialization-State Audit. Held-Out Object-Layout Cross-Task Replication's frozen conduct
record is retained and is not retroactively changed.

## D3C02 — Initialization-State Audit is a reset-only initialization audit

**Date:** 2026-08-16

**Decision:** Initialization-State Audit audits initialization indices `[0,1,2,3,4,5,6,7]` for all
three object-layout task pairs, in both ID and exact frozen OOD scenes. Perform
three clean reset/fingerprint repetitions per task × scene × index: 144 reset-only
operations total. No policy rollout or success analysis occurs in Initialization-State Audit.

**Gate:** requested index must equal resolved index; fingerprints must agree 3/3
within each index and be 8/8 distinct across indices within each task/scene. Fail
closed rather than substitute other indices.


## D034 — Confirmatory Horizon–Delay Operating Envelope validates a local RTC operating region

**Date:** 2026-08-16

**Decision:** Retain the Exploratory OOD–Delay Screening reference `n_action_steps=25, +200 ms`; do not re-optimize Exploratory OOD–Delay Screening from Confirmatory Horizon–Delay Operating Envelope outcomes.

**Evidence:** At +200 ms, pooled ID success is 14/15 at each of h=20,25,30 but 6/15 at h=10. Queue-underrun/hold totals at +200 ms are 1385 for h=10, 72 for h=15, and 0 for h=20/25/30.

**Consequence:** Confirmatory Horizon–Delay Operating Envelope is a supporting configuration-sensitivity analysis. The 25-action reference is described as locally stable, not globally optimal.

## D035 — Held-Out OOD–Delay Horizon Confirmation rejects broad replication and retains one localized candidate

**Date:** 2026-08-16

**Decision:** Do not generalize the Exploratory OOD–Delay Screening localized negative cells as a broad OOD effect.

**Evidence:** `long_stove_moka × object_layout` remains negative at all frozen horizons (`I_20=-0.125`, `I_25=-0.250`, `I_30=-0.125`); robot-initial-state, lighting, and post-hoc sensor noise do not reproduce the negative Exploratory OOD–Delay Screening direction.

**Consequence:** Frame the paper around sparse/heterogeneous OOD × delay interactions, not universal amplification.

## D036 — Held-Out Object-Layout Cross-Task Replication shows task dependence within object-layout OOD

**Date:** 2026-08-16

**Decision:** Preserve Held-Out Object-Layout Cross-Task Replication as completed targeted post-Held-Out OOD–Delay Horizon Confirmation evidence and update the paper claim using its exact outcomes.

**Evidence:**

```text
spatial_transport:
  I20=0.000, I25=0.000, I30=0.000

goal_drawer:
  I20=+0.125, I25=+0.125, I30=0.000

long_stove_moka:
  I20=-0.125, I25=-0.250, I30=-0.125
```

The spatial OOD cells are 8/8 -> 8/8 at all horizons. The goal-drawer OOD cells are also 8/8 -> 8/8 at all horizons. Only `long_stove_moka` shows a negative interaction across all three frozen horizons.

**Consequence:** Do **not** claim that object-layout OOD generally reduces delay tolerance across tasks. The surviving effect is task-dependent and localized to the evaluated multi-stage task. Held-Out Object-Layout Cross-Task Replication remains post-selection evidence, not preregistered family-level confirmation.

## D037 — Initialization-State Audit fails the initialization-diversity capability gate

**Date:** 2026-08-16

**Decision:** Do not run an initialization-generalization rollout experiment for the frozen object-layout variants.

**Evidence:** For all three OOD variants, requested initialization indices 1..7 resolve to 0, leaving one distinct OOD initialization.

**Consequence:** Earlier stages remain valid, but claims are restricted to repeated rollouts from the benchmark-provided OOD initialization. Do not substitute indices or reinterpret rollout seeds as initialization samples.

## D038 — Next test is within-task layout-variant generalization on the surviving task

**Date:** 2026-08-16

**Decision:** Run Object-Layout Generalization on `long_stove_moka` only.

Frozen design:

```text
task = long_stove_moka
suite/task_id = libero_10 / 2
perturbation = Objects Layout
new variants = exactly 3, selected deterministically before outcomes
exclude prior classification_id=1941 / _add_25
RTC
n_action_steps = 25
delay = Native,+200 ms
seeds = [22,23,24,25,26,27,28,29]
libero_episode_index = 0
16 fresh ID + 48 OOD = 64 episodes
```

**Rationale:** Held-Out Object-Layout Cross-Task Replication already supplies clean non-negative cross-task results for the spatial and drawer variants. The highest-value unresolved question is whether the stove/moka negative interaction survives different object-layout instances of the same task.

**Consequence:** Do not spend Object-Layout Generalization compute re-running more layout variants of the Held-Out Object-Layout Cross-Task Replication null tasks. Do not reopen the horizon sweep.

## D039 — Additional multi-stage task replication is conditional and pre-gated

**Date:** 2026-08-16

**Decision:** Multi-Stage Task Generalization runs only if Object-Layout Generalization satisfies the frozen gate:

```text
>=2/3 new stove/moka variants have I<0
AND mean I across the 3 variants <0
AND no unresolved validation/provenance failure
```

If dispatched, use exactly:

```text
task = LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket
suite/task_id = libero_10 / 0
task type = multi_stage_sequential
perturbation = Objects Layout
variants = exactly 3 deterministically frozen before outcomes
RTC
n_action_steps = 25
delay = Native,+200 ms
seeds = [30,31,32,33,34,35,36,37]
libero_episode_index = 0
16 fresh ID + 48 OOD = 64 episodes
```

**Consequence:** If Object-Layout Generalization fails its gate, do not dispatch Multi-Stage Task Generalization merely to search for a favorable multi-stage task.


## D040 — Close Object-Layout Generalization as completed multi-layout replication

**Date:** 2026-08-22

**Decision:** Object-Layout Generalization is complete and passes its frozen gate.

```text
I = -0.375, +0.125, -0.125
2/3 new layouts negative
mean I = -0.125
```

**Consequence:** The `long_stove_moka` signal is not treated as a one-layout artifact, but neither is it treated as universal across layouts.

## D041 — Close Multi-Stage Task Generalization and reject a general multi-stage/turn-count interpretation

**Date:** 2026-08-22

**Decision:** Multi-Stage Task Generalization is complete.

```text
I = -0.375, +0.250, +0.625
1/3 layouts negative
mean I = +0.167
```

**Consequence:** Do not claim that object-layout × delay sensitivity transfers generally to multi-stage tasks, and do not claim monotonic degradation with atomic manipulation turn count.

## D042 — Add Cross-Policy OpenVLA-OFT Diagnostic second-policy external-validity diagnostic

**Date:** 2026-08-22

**Decision:** The next experiment is a small OpenVLA-OFT replication using one prior-null and one prior-negative π0.5 task.

Frozen Cross-Policy OpenVLA-OFT Diagnostic matrix:

```text
policy = moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10
tasks = spatial_transport, long_stove_moka
perturbation = Objects Layout
exact OOD variants = c1773/add_15, c1941/add_25
execution = naive async, not RTC
native action chunk = 8
request threshold = 4
delay = Native,+200 ms
seeds = 38..45
libero_episode_index = 0
64 analysis episodes
```

**Rationale:** After Object-Layout and Multi-Stage Task Generalization, the largest remaining external-validity limitation is the use of a single primary VLA policy. More π0.5 task expansion has lower marginal value than a second-policy diagnostic.

**Consequence:** Cross-Policy OpenVLA-OFT Diagnostic must not be described as an RTC replication or as a controlled architecture ablation.


## D043 — Retain Cross-Policy OpenVLA-OFT Diagnostic as completed native-8 preliminary diagnostic

**Date:** 2026-08-24

**Decision:** Cross-Policy OpenVLA-OFT Diagnostic is complete and immutable at OpenVLA-OFT native/default coverage 8. Its long-task result is floor-limited and its operating point was not independently calibrated.

**Consequence:** Do not overwrite Cross-Policy OpenVLA-OFT Diagnostic. Use it as provenance and a native-stack operating-envelope result.

## D044 — Add OpenVLA-OFT Temporal-Coverage Calibration capability audit and ID-only OpenVLA-OFT coverage calibration

**Date:** 2026-08-24

**Decision:** Before making a final calibrated second-policy claim, determine whether OpenVLA-OFT can legitimately expose more than 8 future actions from a single inference. If tunable, calibrate coverage on ID only with seeds `46..50` using a local-stability rule rather than maximum-success tuning.

**Consequence:** OOD outcomes may not influence coverage selection. Chunk concatenation, action repetition, or any artificial >native horizon is prohibited.

## D045 — Conditional OpenVLA-OFT Temporal-Coverage Calibration Phase B final replication

**Date:** 2026-08-24

**Decision:** If OpenVLA-OFT Temporal-Coverage Calibration Phase A yields a legitimate calibrated operating point warranting a rerun, repeat the exact Cross-Policy OpenVLA-OFT Diagnostic two-task/Objects-Layout/Native-vs-+200-ms diagnostic with fresh seeds `51..58`.

**Consequence:** If the model is natively fixed to exactly 8 actions, do not run an artificial OpenVLA-OFT Temporal-Coverage Calibration Phase B; retain Cross-Policy OpenVLA-OFT Diagnostic and report the fixed native-horizon limitation.

## D043 — Cancel further OpenVLA experiments

**Date:** 2026-08-26

**Decision:** Do not execute OpenVLA-OFT Temporal-Coverage Calibration or any additional OpenVLA-OFT experiment.

**Reason:** External review identified the low number of rollouts in the
existing four-cell interaction estimates as a more important threat to the
paper's central inference than second-policy breadth.

**Consequence:** Cross-Policy OpenVLA-OFT Diagnostic remains historical provenance only. OpenVLA-OFT Temporal-Coverage Calibration is canceled
before execution.

---

## D044 — Replace the final experiment with a fresh high-power Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication replication

**Date:** 2026-08-26

**Decision:** Run `STAGE_3_NEW_HIGH_POWER_REPLICATION.md`.

Freeze:

```text
policy = π0.5
method = RTC
candidate set = union of unique Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication task × perturbation pairs
include Held-Out OOD–Delay Horizon Confirmation post-hoc goal_drawer × sensor_noise = yes
horizons = {20,25,30}
delay = {Native,+200 ms}
fresh seeds = 46..109
n = 64 seeds per unique cell
libero_episode_index = 0
```

The overlapping `long_stove_moka × object_layout` condition is executed once.
Shared ID controls are executed once per base task and reused logically across
perturbation analyses.

Expected new physical rollouts:

```text
OOD = 2,304
ID = 1,152
total = 3,456
```

The old eight-seed Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication rows are not pooled into the primary high-powered
estimates.

---

## D045 — Treat current sparse/heterogeneous interaction language as provisional

**Date:** 2026-08-26

**Decision:** Until High-Power OOD–Delay Replication completes, do not present the low-replication
Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication pattern as established evidence of interaction heterogeneity.

**Reason:** At `n=8`, binary cell proportions move in increments of `0.125`, and
the worst-case standard error of a four-cell interaction is approximately
`0.354`.

**Consequence:** High-Power OOD–Delay Replication may strengthen, weaken, or falsify the existing
interaction narrative. Paper language must follow the high-replication result.
