# OOD × Delay VLA Paper — Active Specification

## Current status

```text
Revised Stage 0: complete
Stage 1 broad OOD screen: complete
Stage 2 local operating-point sensitivity: complete
Stage 3 held-out OOD confirmation: complete
Next: Stage 3B targeted cross-task object-layout replication
```

## Current paper question

> **How does temporal action coverage determine asynchronous VLA robustness to
> inference delay, and do distribution shifts move that robustness boundary?**

Stage 1 did **not** show broad OOD amplification of +200 ms delay. The next
experiments focus on the much stronger horizon-dependence signal.

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


## Next — Stage 3B

`STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md`

Stage 3B is a post-Stage-3 targeted cross-task replication. It tests the exact
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

## Optional — Stage 4

`STAGE_4_VLASH_SUBSET.md`

Run a compact VLASH subset only if official code passes the π0.5/LIBERO
compatibility gate after Stages 2 and 3.

VLASH is **not required** for the core paper.

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
| `STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md` | targeted cross-task object-layout replication |
| `STAGE_4_VLASH_SUBSET.md` | conditional external validation |
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
- OpenVLA-OFT;
- new training/fine-tuning;
- dynamic intervention benchmark;
- hardware claims;
- unrelated async baselines.

## Rough runtime with two A100s

Using the prior rough assumption of 3–5 min/episode:

```text
Stage 2: ~9–15 h
Stage 3: ~7–12 h
Stage 4: ~2–4 h if run
```

Recompute from measured current median episode wall time before dispatch.

## Source anchors

- RTC paper: `https://arxiv.org/abs/2506.07339`
- VLASH: `https://arxiv.org/abs/2512.01031`
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
- Stage 4: if run, pair RTC/VLASH on the exact same task/variant/seed/scene/delay
  episode definition.
