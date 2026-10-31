# Paper Outline

## Working title

**Temporal Coverage Under Shift: Horizon–Latency Robustness of Asynchronous Vision-Language-Action Policies**

## Abstract

1. VLAs have nontrivial inference latency relative to action coverage.
2. RTC is designed for asynchronous delay compensation.
3. Broad LIBERO-Plus Exploratory OOD–Delay Screening screening finds no general OOD amplification of
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

## 4. Latency Calibration and Instrumentation and Protocol Revision

Disclose:
- original 10-action RTC configuration was brittle;
- ID-only revision evaluated 25 actions;
- revision occurred before Exploratory OOD–Delay Screening OOD results;
- Exploratory OOD–Delay Screening used `d*=+200 ms`.

## 5. Broad Exploratory OOD–Delay Screening OOD Screen

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

Central result: at `+200 ms`, pooled success is `14/15` at `n_action_steps=20,25,30`, while the 10-action condition falls to `6/15`. Queue-underrun/hold totals at +200 ms are `1385` for h=10, `72` for h=15, and `0` for h=20/25/30. This supports retaining the frozen Exploratory OOD–Delay Screening point `25/+200` as a locally stable operating point rather than an isolated optimum.

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

Completed result: only `long_stove_moka × object_layout` retains a negative interaction across all three frozen horizons (`I_20=-0.125`, `I_25=-0.250`, `I_30=-0.125`). Robot-initial-state and lighting do not reproduce the Exploratory OOD–Delay Screening negative direction; post-hoc sensor noise also does not. At h=25 and h=30, the prespecified OOD aggregate has no added-delay success drop.


## 7B. Targeted Cross-Task Object-Layout Replication

This section is explicitly post-Held-Out OOD–Delay Horizon Confirmation follow-up evidence.

Test the exact frozen Exploratory OOD–Delay Screening object-layout variants on:

```text
spatial_transport
goal_drawer
```

with the same Held-Out OOD–Delay Horizon Confirmation seed block `[14..21]`, horizons `{20,25,30}`, and
Native/+200 ms RTC conditions. Combine those results with the completed
`long_stove_moka × object_layout` Held-Out OOD–Delay Horizon Confirmation result.

Primary question:

> Is the Held-Out OOD–Delay Horizon Confirmation object-layout interaction reproducible across the other two
> pre-existing task-demand categories, or is it localized to multi-stage
> manipulation?

Do not describe this as preregistered confirmation. Report task-specific
interactions and raw successes/8 before any three-task aggregate.

Held-Out Object-Layout Cross-Task Replication is complete. Cross-task object-layout results are task-dependent: `spatial_transport` has `I=0` at h=20/25/30; `goal_drawer` has `I={+0.125,+0.125,0}`; only `long_stove_moka` remains negative with `I={-0.125,-0.250,-0.125}`. Therefore do not claim object layout is a general perturbation-family effect across tasks.

## 7C. Initialization Capability Audit

Initialization-State Audit requested initialization indices `0..7` for ID and frozen object-layout OOD scenes, with three clean reset repetitions per requested index. For all three OOD variants, indices `1..7` resolved to `0`, so each exposes only one distinct OOD initialization state. The audit therefore failed closed and no initialization-generalization rollout experiment is run.

Paper consequence: explicitly restrict conclusions to repeated rollouts from the benchmark-provided OOD initialization and describe cross-initialization generalization as unsupported by these frozen variants.

## 7D. Within-Task Object-Layout Variant Generalization — Active

Object-Layout Generalization tests exactly three new deterministically selected object-layout variants of `long_stove_moka` only, at RTC `n_action_steps=25`, Native/+200 ms, using fresh seeds `22..29` and `libero_episode_index=0`. Total new execution is 64 episodes (16 fresh ID + 48 OOD).

This asks whether the surviving Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication effect is stable across multiple layouts of the same multi-stage task rather than being specific to `_add_25`.

## 7E. Additional Multi-Stage Task Generalization — Conditional

Multi-Stage Task Generalization runs only if at least 2/3 new Object-Layout Generalization variants have negative interactions and their mean interaction is negative. If dispatched, it evaluates `LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket` (`libero_10`, task 0) with three deterministically frozen object-layout variants, RTC `n_action_steps=25`, Native/+200 ms, fresh seeds `30..37`, and 64 total episodes.

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
- broad Exploratory OOD–Delay Screening null versus localized boundary shifts;
- benchmark implications.

## 11. Limitations

Include:
- one primary VLA checkpoint; Cross-Policy OpenVLA-OFT Diagnostic provides a native-horizon second-policy diagnostic, with OpenVLA-OFT Temporal-Coverage Calibration used to resolve whether OpenVLA-OFT coverage is tunable/calibratable;
- simulation only;
- three base tasks;
- one Exploratory OOD–Delay Screening variant per family;
- ID-based horizon protocol revision;
- possible mismatch between `n_action_steps` and RTC formal horizon;
- floor/ceiling cells;
- Latency Calibration and Instrumentation reused-control provenance;
- selective Held-Out OOD–Delay Horizon Confirmation follow-up;
- Held-Out Object-Layout Cross-Task Replication was selected after observing the Held-Out OOD–Delay Horizon Confirmation object-layout result and reuses the same seed block;
- sensor noise is post-hoc;
- no safety/hardware claim;
- fixed OOD initialization: Initialization-State Audit established that the frozen object-layout variants expose only one distinct OOD reset state;

## 11.5 Second-policy external-validity diagnostic

Cross-Policy OpenVLA-OFT Diagnostic completed OpenVLA-OFT at its native/default 8-action coverage. Spatial transport remained robust under OOD+delay, while the stove/moka task was at/near floor, preventing a clean interaction test.

OpenVLA-OFT Temporal-Coverage Calibration resolves the coverage asymmetry with π0.5:

```text
5A0: verify OpenVLA-OFT native output-horizon semantics
5A: if tunable, calibrate executable temporal coverage on ID only
5B: conditionally rerun the same two-task OOD × delay contrast at the frozen calibrated coverage
```

Do not present Cross-Policy OpenVLA-OFT Diagnostic as a coverage-matched or architecture-controlled comparison. If OpenVLA-OFT Temporal-Coverage Calibration Phase A proves the horizon is fixed at 8, frame Cross-Policy OpenVLA-OFT Diagnostic as evidence about a native-stack temporal-coverage limitation.

## 12. Conclusion

Preferred only if supported:

> Asynchronous VLA robustness is governed by the interaction between inference
> delay and available temporal action coverage. At a robust operating point,
> distribution shift does not universally amplify delay, but selected shifts can
> move the temporal robustness boundary.


## Post-Exploratory OOD–Delay Screening configuration-sensitivity note

Confirmatory Horizon–Delay Operating Envelope uses a same-seed ID matrix over:

```text
n_action_steps = 10,15,20,25,30,35
delay = Native,+100,+200,+300 ms
seeds = 5..9
```

Native controls at every horizon separate the horizon main effect from incremental
added-delay sensitivity.

Held-Out OOD–Delay Horizon Confirmation horizons are frozen at `{20,25,30}` before Confirmatory Horizon–Delay Operating Envelope execution. This is a
symmetric ±5-action neighborhood around the completed Exploratory OOD–Delay Screening reference at 25,
not a horizon set selected after viewing Confirmatory Horizon–Delay Operating Envelope.

## Post-Initialization-State Audit completed follow-ups

Object-Layout Generalization: negative interaction on 2/3 new `long_stove_moka` layouts; mean `I=-0.125`.

Multi-Stage Task Generalization: negative interaction on 1/3 layouts on the second multi-stage task; mean `I=+0.167`.

These results support a heterogeneous task/layout story and weaken any monotonic multi-turn interpretation.

## Active next experiment

OpenVLA-OFT Temporal-Coverage Calibration is defined in `STAGE_5_OPENVLA_OFT_COVERAGE_CALIBRATION_AND_FINAL_REPLICATION.md`.

## High-Power OOD–Delay Replication — final precision experiment

Before final paper freeze, repeat the complete unique Held-Out OOD–Delay Horizon Confirmation / Held-Out Object-Layout Cross-Task Replication
condition set at `n=64` fresh seeds/cell.

This experiment is designed specifically to address the uncertainty limitation
in the existing interaction table:

```text
old Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication: n = 8 per cell
High-Power OOD–Delay Replication:    n = 64 fresh seeds per cell
```

The main Results revision after completion should:

1. show the high-replication interaction-versus-horizon figure in place of the
   low-n Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication figure;
2. report all six candidate conditions, including the post-hoc sensor-noise row;
3. directly test cross-task object-layout contrasts rather than inferring
   heterogeneity from separate significance calls;
4. state clearly whether the original sparse/heterogeneous narrative survives.

No further OpenVLA experiment is planned. Cross-Policy OpenVLA-OFT Diagnostic may remain in an appendix or
limitations discussion as preliminary provenance, but it is not part of the
final experimental critical path.
