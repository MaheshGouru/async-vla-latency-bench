# OOD × Delay Benchmark Docs

## Current execution status

```text
Latency Calibration and Instrumentation  COMPLETE
Exploratory OOD–Delay Screening  COMPLETE
Confirmatory Horizon–Delay Operating Envelope  COMPLETE
Held-Out OOD–Delay Horizon Confirmation  COMPLETE
Held-Out Object-Layout Cross-Task Replication COMPLETE
Initialization-State Audit COMPLETE — benchmark initialization-diversity gate failed closed
High-Power OOD–Delay Replication COMPLETE — 64-seed high-power replication
Object-Layout Generalization COMPLETE
Multi-Stage Task Generalization COMPLETE
Cross-Policy OpenVLA-OFT Diagnostic ACTIVE NEXT — second-policy OpenVLA-OFT replication
```

Initialization-State Audit established that each frozen LIBERO-Plus object-layout OOD variant exposes only one distinct initialization state: requested indices `1..7` resolve to index `0`. Earlier rollout results remain valid, but no claim of robustness across the environment-initialization distribution is supported.

The two generalization studies are complete. Object-Layout Generalization reproduced a negative `long_stove_moka × object_layout` interaction in 2/3 new layouts (mean `I=-0.125`); Multi-Stage Task Generalization reproduced a negative interaction in only 1/3 layouts on the second multi-stage task (mean `I=+0.167`). The active next experiment is Cross-Policy OpenVLA-OFT Diagnostic, defined in `STAGE_4_SECOND_POLICY_OPENVLA_OFT.md`.

---

## Current status

```text
Revised Latency Calibration and Instrumentation: complete
Exploratory OOD–Delay Screening broad OOD screen: complete
Confirmatory Horizon–Delay Operating Envelope local operating-point sensitivity: complete
Held-Out OOD–Delay Horizon Confirmation fresh-rollout OOD confirmation: complete
Held-Out Object-Layout Cross-Task Replication: complete
Initialization-State Audit: complete; failed closed
High-Power OOD–Delay Replication: complete; 3,456 valid rows
Object-Layout Generalization: within-task layout-variant generalization complete
Multi-Stage Task Generalization second multi-stage task generalization: complete
Next: Cross-Policy OpenVLA-OFT Diagnostic second-policy OpenVLA-OFT diagnostic
```

## Current paper question

> **How does temporal action coverage determine asynchronous VLA robustness to
> inference delay, and do distribution shifts move that robustness boundary?**

Exploratory OOD–Delay Screening did **not** show broad OOD amplification of +200 ms delay. The completed follow-ups show a strong temporal-action-coverage effect and sparse, task/layout-dependent OOD × delay interactions. The 64-seed High-Power OOD–Delay Replication is the final primary-policy evidence; the preliminary Cross-Policy OpenVLA-OFT Diagnostic is separate cross-policy evidence.

## Completed Latency Calibration and Instrumentation

Final revised calibration:

```text
n_action_steps = 25
3 tasks × 2 methods × 5 delays [0,100,200,300,400] × 6 seeds
= 180 episodes

selected d* = +200 ms
```

The 25-action revision used ID-only evidence after the 10-action RTC setting
performed poorly.

## Completed Exploratory OOD–Delay Screening

```text
3 tasks
× 7 LIBERO-Plus perturbation families
× 2 delays [Native, Native +200 ms]
× 2 methods [Naive async, RTC]
× 5 seeds
= 420 OOD episodes

+ 60 ID analysis controls
= 480 Exploratory OOD–Delay Screening analysis rows
```

Headline result:

```text
ID:  60.0% -> 56.7%
OOD: 60.0% -> 58.1%
pooled I ≈ +1.4 percentage points
```

Therefore: **no broad evidence that OOD amplifies +200 ms delay at
`n_action_steps=25`.**

## Completed — Confirmatory Horizon–Delay Operating Envelope

`STAGE_2_LOCAL_OPERATING_POINT_SENSITIVITY.md`

Required RTC grid:

```text
n_action_steps = 10,15,20,25,30,35
delay = Native,100,200,300 ms
3 ID tasks
5 new seeds
= 360 RTC episodes
```

Total Confirmatory Horizon–Delay Operating Envelope: **360 new episodes**.

Combined required Confirmatory Horizon–Delay Operating Envelope + primary Held-Out OOD–Delay Horizon Confirmation: **600 episodes**. Including the
Held-Out OOD–Delay Horizon Confirmation post-hoc sensor-noise replication gives **648 episodes**.

## Completed — Held-Out OOD–Delay Horizon Confirmation

`STAGE_3_OOD_HORIZON_CONFIRMATION.md`

Prespecified confirmatory families:
- Object layout
- Robot initial state
- Lighting

Post-hoc replication:
- Sensor noise

Use:

```text
RTC
n_action_steps = 20,25,30
delay = Native,+200 ms
held-out seeds = 14..21
```

The Held-Out OOD–Delay Horizon Confirmation horizons are frozen **before Confirmatory Horizon–Delay Operating Envelope execution** as the symmetric
local neighborhood `{20,25,30}` around the completed Exploratory OOD–Delay Screening reference at 25
actions. They must not be changed after viewing Confirmatory Horizon–Delay Operating Envelope outcomes.

With shared ID controls: **288 new episodes**.


## Completed — Held-Out Object-Layout Cross-Task Replication

`STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md`

Held-Out Object-Layout Cross-Task Replication is a completed post-Held-Out OOD–Delay Horizon Confirmation targeted cross-task replication. It tests the exact
frozen Exploratory OOD–Delay Screening object-layout variants on the two remaining task-demand categories:

```text
spatial_transport × object_layout
goal_drawer × object_layout
RTC
n_action_steps = 20,25,30
delay = Native,+200 ms
seeds = 14..21
initialization_index_or_id = libero_episode_index:0
```

Reuse the 48 existing Held-Out OOD–Delay Horizon Confirmation `goal_drawer` ID controls. Run new matching ID
controls for `spatial_transport`; Held-Out OOD–Delay Horizon Confirmation did not contain spatial ID controls.

```text
96 new OOD + 48 new spatial ID = 144 new episodes
```

No new `long_stove_moka` episodes are run; its completed Held-Out OOD–Delay Horizon Confirmation ID/object-layout
rows form the third task in the final cross-task analysis.

## Completed — Initialization-State Audit

`STAGE_3C_INITIALIZATION_AUDIT.md`

Initialization-State Audit performed no policy rollouts. It audited indices `{0..7}` by three repeated clean resets for every ID/object-layout task scene. The OOD variants failed the eight-distinct-initialization capability gate because requested indices `1..7` resolved to `0`; each frozen OOD variant exposes only one distinct initialization through this interface.

```text
3 tasks × 2 scenes × 8 indices × 3 repeated resets = 144 reset-only operations
```


## Out of active scope


## Active files

| File | Purpose |
|---|---|
| `RESEARCH_CONTEXT.md` | current scientific framing |
| `STAGE_0_LATENCY_CALIBRATION.md` | historical calibration spec |
| `STAGE_0_N_ACTION_STEPS_25_CONDUCT.md` | actual revised Latency Calibration and Instrumentation conduct |
| `STAGE_1_EXPLORATORY_SCREEN.md` | broad OOD × delay screen + result addendum |
| `STAGE_2_LOCAL_OPERATING_POINT_SENSITIVITY.md` | completed temporal-coverage sensitivity experiment |
| `STAGE_2_HORIZON_LATENCY_PHASE_DIAGRAM.md` | superseded full-grid pointer retained for provenance |
| `STAGE_3_OOD_HORIZON_CONFIRMATION.md` | held-out OOD × horizon follow-up |
| `STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md` | completed targeted cross-task object-layout replication |
| `STAGE_3C_INITIALIZATION_AUDIT.md` | reset-only determinism/distinctness audit over indices 0..7 |
| `EXPERIMENT_A_OBJECT_LAYOUT_VARIANT_GENERALIZATION.md` | completed within-task multi-layout replication |
| `EXPERIMENT_B_ADDITIONAL_MULTI_STAGE_TASK_GENERALIZATION.md` | completed second multi-stage task replication |
| `STAGE_4_SECOND_POLICY_OPENVLA_OFT.md` | completed native-8 second-policy preliminary diagnostic |
| `STAGE_5_OPENVLA_OFT_COVERAGE_CALIBRATION_AND_FINAL_REPLICATION.md` | canceled before execution; retained for provenance |
| `STAGE_3_NEW_HIGH_POWER_REPLICATION.md` | **completed final 64-seed rerun of the Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication matrix** |
| `STAGE_2_CONFIRMATORY_FOLLOWUP.md` | deprecated pointer retained for provenance |
| `EXPERIMENT_MATRIX_POST_STAGE1.md` | concise new-run matrix |
| `METRICS_AND_LOGGING.md` | canonical metrics/logging |
| `PAPER_OUTLINE.md` | revised paper structure |
| `IMPLEMENTATION_STATUS.md` | active checklist |
| `DECISIONS.md` | frozen/superseding decisions |
| `KNOWN_ISSUES.md` | current risks |

## Critical-path exclusions

Do not add:
- SmolVLA;
- new training/fine-tuning;
- dynamic intervention benchmark;
- hardware claims;
- unrelated async baselines.

## Rough runtime with two A100s

Using the prior rough assumption of 3–5 min/episode:

```text
Confirmatory Horizon–Delay Operating Envelope: ~9–15 h
Held-Out OOD–Delay Horizon Confirmation: ~7–12 h
```

Recompute from measured current median episode wall time before dispatch.

## Source anchors

- RTC paper: `https://arxiv.org/abs/2506.07339`
- LIBERO-Plus: `https://arxiv.org/abs/2510.13626`
- LIBERO-Plus code: `https://github.com/sylvestf/LIBERO-plus`


## Episode matching

See:

```text
EPISODE_MATCHING_AND_VARIANT_FREEZE.md
```

Future stages use new seed blocks rather than recycling Latency Calibration and Instrumentation/1 episodes.

- Confirmatory Horizon–Delay Operating Envelope: pair horizon/delay cells internally on task + seed + initialization.
- Held-Out OOD–Delay Horizon Confirmation: reuse the **exact Exploratory OOD–Delay Screening OOD variant identities** with held-out seeds.

## Active final experiment

OpenVLA OpenVLA-OFT Temporal-Coverage Calibration is canceled before execution. No additional OpenVLA policy runs are planned.

Run exactly:

```text
STAGE_3_NEW_HIGH_POWER_REPLICATION.md
```

High-Power OOD–Delay Replication reruns the union of Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication with no new scientific factor:

```text
π0.5 + RTC
6 exact frozen task × perturbation pairs
horizons = 20,25,30
delay = Native,+200 ms
fresh seeds = 46..109
64 seeds per unique cell
shared ID controls
3,456 new physical policy episodes
```

The purpose is to determine whether the earlier low-replication interaction pattern is reproducible or was dominated by rollout noise.
