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
6. Mention VLASH only if Stage 4 is actually completed.

## 1. Introduction

Primary question:

> How much temporal action coverage does asynchronous VLA execution need to absorb
> inference delay, and does distribution shift alter that requirement?

Contributions should be empirical, not algorithmic.

## 2. Related Work

- action chunking and RTC;
- asynchronous/future-state alignment including VLASH and FutureRTC;
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

Central section.

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

## 8. Temporal Mechanism Analysis

Analyze:
- action age;
- logical delay;
- queue occupancy;
- discards;
- RTC frozen/guided/fresh regions where available.

Do not treat action age as a monotonic quality score.

## 9. Conditional VLASH Validation

Only if compatibility gate passes.

Question:
> Does a different asynchronous alignment strategy show the same selected
> OOD-under-delay behavior?

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
- sensor noise is post-hoc;
- no safety/hardware claim.

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
