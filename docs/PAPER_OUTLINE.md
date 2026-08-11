# Paper Outline

## Working title

**Robustness Under Delay: OOD × Inference-Latency Interactions in Vision-Language-Action Policies**

## Abstract

Cover only:

1. action-chunked VLAs are deployed with nonzero inference latency;
2. robustness benchmarks typically evaluate distribution shift without explicitly asking whether the shift changes tolerance to delay;
3. we cross LIBERO-Plus perturbations with calibrated asynchronous inference delay;
4. we organize results along perturbation mechanism and task behavioral demand;
5. we compare Naive async and RTC and use action age as mechanism analysis;
6. state the strongest replicated result, including nulls/counterexamples when relevant.

## 1. Introduction

Motivating question:

> Can native-latency robustness predict robustness under delayed asynchronous execution?

Contributions:

1. controlled OOD × delay evaluation across all seven LIBERO-Plus perturbation families;
2. two-axis analysis:
   - task behavioral demand;
   - perturbation mechanism;
3. matched Naive async vs RTC comparison;
4. per-action temporal provenance/action-age diagnostics.

Do not claim a new controller.

## 2. Related Work

### 2.1 VLA robustness

- LIBERO / LIBERO-Plus;
- robustness taxonomies by environment, observation, instruction, robot/action state.

### 2.2 Asynchronous / real-time VLA execution

- RTC;
- future-state, streaming, corrective, and adaptive-horizon methods as context.

### 2.3 Temporal freshness

- distinguish request latency from the age of information behind executed actions.

## 3. Experimental Taxonomy

### 3.1 Task-demand groups

```text
Single-stage transport
Articulated/contact-rich
Multi-stage/sequential
```

State explicitly that this is our task-level analysis taxonomy.

### 3.2 Perturbation mechanism

```text
Trajectory adaptation
Perceptual localization
Appearance invariance
Semantic grounding
```

Map all seven official LIBERO-Plus perturbation families into these groups.

State explicitly that the mechanism grouping is introduced for this study.

## 4. Experimental Setup

### 4.1 Policy

```text
lerobot/pi05_libero_finetuned
n_action_steps = 25
```

### 4.2 Tasks

```text
libero_spatial:2
libero_goal:0
libero_10:2
```

### 4.3 Execution methods

```text
Naive async
RTC
```

### 4.4 Temporal instrumentation

- request latency;
- logical delay;
- action age;
- queue occupancy;
- continuity diagnostics.

### 4.5 OOD variants

- all seven LIBERO-Plus perturbation families;
- one deterministic moderate-difficulty variant per task × family;
- variant mapping frozen before policy outcomes.

## 5. ID-Only Latency Calibration

Show the calibration curve:

```text
Native
Native +100
Native +200
Native +300
Native +400
Native +500
Native +600
Native +700 ms
```

Explain the predefined `d*` selection rule.

The key methodological point:

> `d*` is selected without examining OOD outcomes.

Main paper: compact plot/table.

Appendix: full task × method calibration table.

## 6. Broad Exploratory OOD × Delay Screen

Report the **entire** seven-family screen.

### 6.1 Four-cell results

For every task × perturbation × method:

```text
ID-low
ID-high
OOD-low
OOD-high
I
```

### 6.2 By perturbation family

Question:

> Which perturbation families most reduce delay tolerance?

### 6.3 By perturbation mechanism

Question:

> Do trajectory adaptation, perceptual localization, appearance invariance, and semantic grounding exhibit different temporal sensitivity?

Treat mechanism-level results as descriptive because group sizes differ.

### 6.4 By task behavioral demand

Question:

> Does the same perturbation interact differently with delay across task demands?

### 6.5 Naive async vs RTC

Question:

> Does asynchronous execution strategy change the OOD × delay interaction or ranking?

## 7. Confirmatory Follow-Up

Only include as confirmatory if it follows `STAGE_2_CONFIRMATORY_FOLLOWUP.md`.

Report:

- frozen selection rule;
- exploratory seeds excluded from the held-out confirmation calculation;
- held-out success counts and intervals;
- interaction estimate;
- whether the Stage 1 direction replicated.

The complete Stage 1 screen remains visible in the paper or appendix.

## 8. Temporal Mechanism Analysis

Use action age and queue behavior to explain—not define—the main result.

Potential analyses:

- action-age distributions across ID/OOD and low/high;
- successful vs failed episodes;
- Naive async vs RTC;
- whether a perturbation changes success without changing model request latency.

Avoid causal language.

## 9. Discussion

Discuss:

- whether static robustness predicts delayed robustness;
- which perturbation mechanisms appear most temporally sensitive;
- dependence on behavioral demand;
- implications for evaluating VLA deployment;
- what RTC does and does not protect against.

## 10. Limitations

Required:

- one VLA checkpoint;
- simulation only;
- three base tasks;
- one selected variant per task × perturbation family in Stage 1;
- exploratory Stage 1 has only two seeds;
- internal taxonomy is not canonical;
- LIBERO-Plus perturbations may have unequal difficulty;
- confirmation is selective by design and must be reported transparently;
- no safety or hardware claim.

## 11. Conclusion

Preferred conclusion form:

> Static OOD robustness and temporal robustness should not be treated as interchangeable. Their interaction depends on the perturbation, behavioral demand, and execution strategy.

Only use this conclusion if the data support it.

## Main figures

Target:

1. experiment/taxonomy schematic;
2. Stage 0 latency calibration curve;
3. Naive-async OOD × delay interaction heatmap;
4. RTC OOD × delay interaction heatmap;
5. interaction by perturbation mechanism/task demand;
6. confirmatory interaction plot;
7. action-age diagnostic.

## Appendix

Include:

- all 192 Stage 1 analysis rows/cells summarized;
- resolved LIBERO-Plus variant mapping;
- complete null results;
- invalid-run accounting;
- environment/checkpoint revisions;
- latency distributions;
- queue diagnostics;
- failure-mode table.

## Claim gate

Do not submit a paper whose only conclusion is:

> More delay reduces success.

A useful result should support at least one of:

- static OOD robustness fails to predict delayed robustness;
- perturbation mechanisms have different delay interactions;
- behavioral demand changes the interaction;
- RTC/Naive ranking changes under OOD + delay;
- action-age diagnostics reveal a temporal failure mode hidden by request latency.
