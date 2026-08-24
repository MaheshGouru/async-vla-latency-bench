# OOD × Delay Benchmark Docs

## Current execution status

```text
Stage 0  COMPLETE
Stage 1  COMPLETE
Stage 2  COMPLETE
Stage 3  COMPLETE
Stage 3B COMPLETE
Stage 3C COMPLETE — benchmark initialization-diversity gate failed closed
Experiment A COMPLETE
Experiment B COMPLETE
Stage 4 ACTIVE NEXT — second-policy OpenVLA-OFT replication
```

Stage 3C established that each frozen LIBERO-Plus object-layout OOD variant exposes only one distinct initialization state: requested indices `1..7` resolve to index `0`. Earlier rollout results remain valid, but no claim of robustness across the environment-initialization distribution is supported.

Experiments A and B are complete. Experiment A reproduced a negative `long_stove_moka × object_layout` interaction in 2/3 new layouts (mean `I=-0.125`); Experiment B reproduced a negative interaction in only 1/3 layouts on the second multi-stage task (mean `I=+0.167`). The active next experiment is Stage 4, defined in `STAGE_4_SECOND_POLICY_OPENVLA_OFT.md`.

---

## Current status

```text
Revised Stage 0: complete
Stage 1 broad OOD screen: complete
Stage 2 local operating-point sensitivity: complete
Stage 3 fresh-rollout OOD confirmation: complete
Stage 3B targeted cross-task object-layout replication: complete
Stage 3C initialization audit: complete; failed closed
Experiment A within-task layout-variant generalization: complete
Experiment B second multi-stage task generalization: complete
Next: Stage 4 second-policy OpenVLA-OFT diagnostic
```

## Current paper question

> **How does temporal action coverage determine asynchronous VLA robustness to
> inference delay, and do distribution shifts move that robustness boundary?**

Stage 1 did **not** show broad OOD amplification of +200 ms delay. The completed follow-ups show a strong temporal-action-coverage effect and sparse, task/layout-dependent OOD × delay interactions. Stage 4 now tests cross-policy external validity.

## Completed Stage 0

Final revised calibration:

```text
n_action_steps = 25
3 tasks × 2 methods × 5 delays [0,100,200,300,400] × 6 seeds
= 180 episodes

selected d* = +200 ms
```

The 25-action revision used ID-only evidence after the 10-action RTC setting
performed poorly.

## Completed Stage 1

```text
3 tasks
× 7 LIBERO-Plus perturbation families
× 2 delays [Native, Native +200 ms]
× 2 methods [Naive async, RTC]
× 5 seeds
= 420 OOD episodes

+ 60 ID analysis controls
= 480 Stage 1 analysis rows
```

Headline result:

```text
ID:  60.0% -> 56.7%
OOD: 60.0% -> 58.1%
pooled I ≈ +1.4 percentage points
```

Therefore: **no broad evidence that OOD amplifies +200 ms delay at
`n_action_steps=25`.**

## Completed — Stage 2

`STAGE_2_LOCAL_OPERATING_POINT_SENSITIVITY.md`

Required RTC grid:

```text
n_action_steps = 10,15,20,25,30,35
delay = Native,100,200,300 ms
3 ID tasks
5 new seeds
= 360 RTC episodes
```

Total Stage 2: **360 new episodes**.

Combined required Stage 2 + primary Stage 3: **600 episodes**. Including the
Stage 3 post-hoc sensor-noise replication gives **648 episodes**.

## Completed — Stage 3

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

The Stage 3 horizons are frozen **before Stage 2 execution** as the symmetric
local neighborhood `{20,25,30}` around the completed Stage 1 reference at 25
actions. They must not be changed after viewing Stage 2 outcomes.

With shared ID controls: **288 new episodes**.


## Completed — Stage 3B

`STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md`

Stage 3B is a completed post-Stage-3 targeted cross-task replication. It tests the exact
frozen Stage 1 object-layout variants on the two remaining task-demand categories:

```text
spatial_transport × object_layout
goal_drawer × object_layout
RTC
n_action_steps = 20,25,30
delay = Native,+200 ms
seeds = 14..21
initialization_index_or_id = libero_episode_index:0
```

Reuse the 48 existing Stage 3 `goal_drawer` ID controls. Run new matching ID
controls for `spatial_transport`; Stage 3 did not contain spatial ID controls.

```text
96 new OOD + 48 new spatial ID = 144 new episodes
```

No new `long_stove_moka` episodes are run; its completed Stage 3 ID/object-layout
rows form the third task in the final cross-task analysis.

## Completed — Stage 3C initialization audit

`STAGE_3C_INITIALIZATION_AUDIT.md`

Stage 3C performed no policy rollouts. It audited indices `{0..7}` by three repeated clean resets for every ID/object-layout task scene. The OOD variants failed the eight-distinct-initialization capability gate because requested indices `1..7` resolved to `0`; each frozen OOD variant exposes only one distinct initialization through this interface.

```text
3 tasks × 2 scenes × 8 indices × 3 repeated resets = 144 reset-only operations
```


## Out of active scope


## Active files

| File | Purpose |
|---|---|
| `RESEARCH_CONTEXT.md` | current scientific framing |
| `STAGE_0_LATENCY_CALIBRATION.md` | historical calibration spec |
| `STAGE_0_N_ACTION_STEPS_25_CONDUCT.md` | actual revised Stage 0 conduct |
| `STAGE_1_EXPLORATORY_SCREEN.md` | broad OOD × delay screen + result addendum |
| `STAGE_2_LOCAL_OPERATING_POINT_SENSITIVITY.md` | highest-priority next experiment |
| `STAGE_2_HORIZON_LATENCY_PHASE_DIAGRAM.md` | superseded full-grid pointer retained for provenance |
| `STAGE_3_OOD_HORIZON_CONFIRMATION.md` | held-out OOD × horizon follow-up |
| `STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md` | completed targeted cross-task object-layout replication |
| `STAGE_3C_INITIALIZATION_AUDIT.md` | reset-only determinism/distinctness audit over indices 0..7 |
| `EXPERIMENT_A_OBJECT_LAYOUT_VARIANT_GENERALIZATION.md` | completed within-task multi-layout replication |
| `EXPERIMENT_B_ADDITIONAL_MULTI_STAGE_TASK_GENERALIZATION.md` | completed second multi-stage task replication |
| `STAGE_4_SECOND_POLICY_OPENVLA_OFT.md` | completed native-8 second-policy preliminary diagnostic |
| `STAGE_5_OPENVLA_OFT_COVERAGE_CALIBRATION_AND_FINAL_REPLICATION.md` | active OpenVLA-OFT coverage audit/calibration + conditional final replication |
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
Stage 2: ~9–15 h
Stage 3: ~7–12 h
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

Future stages use new seed blocks rather than recycling Stage 0/1 episodes.

- Stage 2: pair horizon/delay cells internally on task + seed + initialization.
- Stage 3: reuse the **exact Stage 1 OOD variant identities** with held-out seeds.

## Active post-Stage-3C experiment specifications

Experiments A and B are complete. Stage 4 is also complete as a preliminary/native-stack OpenVLA-OFT diagnostic at 8-action coverage.

The active next protocol is:

- `STAGE_5_OPENVLA_OFT_COVERAGE_CALIBRATION_AND_FINAL_REPLICATION.md` — first audit whether OpenVLA-OFT can legitimately expose more than 8 future actions from one inference; if tunable, perform ID-only coverage calibration and freeze a locally stable operating point; then conditionally rerun the same two-task OOD × delay diagnostic with fresh seeds.

## Results ledger

`COMPLETED_RESULTS_LEDGER.md` is the authoritative concise numerical summary for completed Stages 1, 2, 3, 3B, and 3C. Stage-3B numerical outcomes are integrated from the completed result archive.


## Final active execution order

1. Run Stage 5A0 capability audit.
2. If OpenVLA-OFT is fixed to an 8-action native horizon, stop the coverage sweep and retain Stage 4 as the native-horizon second-policy diagnostic.
3. If multiple legitimate coverages are available from one inference, run Stage 5A on ID only using fresh seeds `46..50` and freeze a locally stable operating point without consulting OOD outcomes.
4. If warranted by Stage 5A, run Stage 5B on the exact Stage-4 task/variant contrast with fresh seeds `51..58`.

Do not manufacture longer OpenVLA coverage by concatenating predictions or repeating actions.


### Stage 4 history note

`STAGE_4_SECOND_POLICY_OPENVLA_OFT.md` is the frozen pre-run Stage 4 specification and must not be modified retroactively.

Post-run Stage 4 results, caveats, and the motivation for Stage 5 are recorded separately in:

```text
STAGE_4_RESULTS_AND_INTERPRETATION.md
```
