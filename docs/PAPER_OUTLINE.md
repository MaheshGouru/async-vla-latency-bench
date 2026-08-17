# Paper Outline

## Working title

**Temporal Coverage Under Shift: Horizon–Latency Robustness of Asynchronous Vision-Language-Action Policies**

## Abstract

1. VLAs have nontrivial inference latency relative to action coverage.
2. RTC is designed for asynchronous delay compensation.
3. Broad LIBERO-Plus Stage 1 screening finds no general OOD amplification of
   +200 ms delay at a robust 25-action configuration.
4. Temporal configuration is much more consequential: 10-action RTC is brittle
   while 25-action RTC is strong.
5. We map the RTC horizon × latency operating envelope and test whether selected
   OOD shifts move it.

## 1. Introduction

Primary question:

> How much temporal action coverage does asynchronous VLA execution need to absorb
> inference delay, and does distribution shift alter that requirement?

Contributions should be empirical, not algorithmic.

## 2. Related Work

- action chunking and RTC;
- LIBERO-Plus robustness;
- delayed control / temporal freshness.

## 3. Setup and Temporal Definitions

Report:
- π0.5 checkpoint;
- three LIBERO tasks;
- RTC and Naive async;
- native request latency;
- added delay;
- logical delay in control steps;
- configured `n_action_steps`;
- normalized temporal coverage.

Do not equate `n_action_steps` to RTC paper `s` without validation.

## 4. Stage 0 and Protocol Revision

Disclose:
- original 10-action RTC configuration was brittle;
- ID-only revision evaluated 25 actions;
- revision occurred before Stage 1 OOD results;
- Stage 1 used `d*=+200 ms`.

## 5. Broad Stage 1 OOD Screen

### Aggregate result

```text
ID:  60.0% -> 56.7%
OOD: 60.0% -> 58.1%
I ≈ +1.4 pp
```

Conclusion:
> No broad evidence of OOD amplification at the 25-action operating point.

### Method dependence
Report RTC versus Naive with floor/ceiling caveats.

### Local heterogeneity
Show full heatmap and distinguish prespecified tied families from post-hoc
sensor-noise observation.

## 6. RTC Local Horizon × Latency Sensitivity

Central result: at `+200 ms`, pooled success is `14/15` at `n_action_steps=20,25,30`, while the 10-action condition falls to `6/15`. Queue-underrun/hold totals at +200 ms are `1385` for h=10, `72` for h=15, and `0` for h=20/25/30. This supports retaining the frozen Stage-1 point `25/+200` as a locally stable operating point rather than an isolated optimum.

Figures:
- per-task local success heatmaps over `n_action_steps × added delay`;
- normalized coverage plot;
- descriptive local boundary versus coverage.

Question:
> Does the 10-action -> 25-action difference form a coherent temporal boundary?

## 7. OOD × Horizon Confirmation

Held-out seeds.

Prespecified:
- long × object layout;
- goal × robot initial state;
- goal × lighting.

Post-hoc:
- goal × sensor noise.

Main plot:
```text
I_h versus n_action_steps
```

Completed result: only `long_stove_moka × object_layout` retains a negative interaction across all three frozen horizons (`I_20=-0.125`, `I_25=-0.250`, `I_30=-0.125`). Robot-initial-state and lighting do not reproduce the Stage-1 negative direction; post-hoc sensor noise also does not. At h=25 and h=30, the prespecified OOD aggregate has no added-delay success drop.


## 7B. Targeted Cross-Task Object-Layout Replication

This section is explicitly post-Stage-3 follow-up evidence.

Test the exact frozen Stage 1 object-layout variants on:

```text
spatial_transport
goal_drawer
```

with the same Stage 3 seed block `[14..21]`, horizons `{20,25,30}`, and
Native/+200 ms RTC conditions. Combine those results with the completed
`long_stove_moka × object_layout` Stage 3 result.

Primary question:

> Is the Stage 3 object-layout interaction reproducible across the other two
> pre-existing task-demand categories, or is it localized to multi-stage
> manipulation?

Do not describe this as preregistered confirmation. Report task-specific
interactions and raw successes/8 before any three-task aggregate.

Stage 3B is complete. Cross-task object-layout results are task-dependent: `spatial_transport` has `I=0` at h=20/25/30; `goal_drawer` has `I={+0.125,+0.125,0}`; only `long_stove_moka` remains negative with `I={-0.125,-0.250,-0.125}`. Therefore do not claim object layout is a general perturbation-family effect across tasks.

## 7C. Initialization Capability Audit

Stage 3C requested initialization indices `0..7` for ID and frozen object-layout OOD scenes, with three clean reset repetitions per requested index. For all three OOD variants, indices `1..7` resolved to `0`, so each exposes only one distinct OOD initialization state. The audit therefore failed closed and no initialization-generalization rollout experiment is run.

Paper consequence: explicitly restrict conclusions to repeated rollouts from the benchmark-provided OOD initialization and describe cross-initialization generalization as unsupported by these frozen variants.

## 7D. Within-Task Object-Layout Variant Generalization — Active

Experiment A tests exactly three new deterministically selected object-layout variants of `long_stove_moka` only, at RTC `n_action_steps=25`, Native/+200 ms, using fresh seeds `22..29` and `libero_episode_index=0`. Total new execution is 64 episodes (16 fresh ID + 48 OOD).

This asks whether the surviving Stage-3/3B effect is stable across multiple layouts of the same multi-stage task rather than being specific to `_add_25`.

## 7E. Additional Multi-Stage Task Generalization — Conditional

Experiment B runs only if at least 2/3 new Experiment-A variants have negative interactions and their mean interaction is negative. If dispatched, it evaluates `LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket` (`libero_10`, task 0) with three deterministically frozen object-layout variants, RTC `n_action_steps=25`, Native/+200 ms, fresh seeds `30..37`, and 64 total episodes.

This tests whether a repeated within-task effect extends to another multi-stage task.

## 8. Temporal Mechanism Analysis

Analyze:
- action age;
- logical delay;
- queue occupancy;
- discards;
- RTC frozen/guided/fresh regions where available.

Do not treat action age as a monotonic quality score.

## 10. Discussion

- temporal coverage versus raw latency;
- coverage/reactivity tradeoff;
- broad Stage 1 null versus localized boundary shifts;
- benchmark implications.

## 11. Limitations

Include:
- one VLA checkpoint;
- simulation only;
- three base tasks;
- one Stage 1 variant per family;
- ID-based horizon protocol revision;
- possible mismatch between `n_action_steps` and RTC formal horizon;
- floor/ceiling cells;
- Stage 0 reused-control provenance;
- selective Stage 3 follow-up;
- Stage 3B was selected after observing the Stage 3 object-layout result and reuses the same seed block;
- sensor noise is post-hoc;
- no safety/hardware claim;
- fixed OOD initialization: Stage 3C established that the frozen object-layout variants expose only one distinct OOD reset state;

## 12. Conclusion

Preferred only if supported:

> Asynchronous VLA robustness is governed by the interaction between inference
> delay and available temporal action coverage. At a robust operating point,
> distribution shift does not universally amplify delay, but selected shifts can
> move the temporal robustness boundary.


## Post-Stage-1 configuration-sensitivity note

Stage 2 uses a same-seed ID matrix over:

```text
n_action_steps = 10,15,20,25,30,35
delay = Native,+100,+200,+300 ms
seeds = 5..9
```

Native controls at every horizon separate the horizon main effect from incremental
added-delay sensitivity.

Stage 3 horizons are frozen at `{20,25,30}` before Stage 2 execution. This is a
symmetric ±5-action neighborhood around the completed Stage 1 reference at 25,
not a horizon set selected after viewing Stage 2.

## Post-Stage-3C active follow-up

The next experiment is `long_stove_moka` **within-task layout-variant generalization**: three new object-layout variants, RTC, `n_action_steps=25`, Native/+200 ms, seeds `22..29`, 64 episodes. Only if its frozen gate passes should the additional `libero_10` multi-stage task be run with seeds `30..37`.
