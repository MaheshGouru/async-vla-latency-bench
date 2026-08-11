# Research Context

## Working title

**Robustness Under Delay: OOD × Inference-Latency Interactions in Vision-Language-Action Policies**

Do not use `StaleBench` as the submission name unless the name collision is resolved.

## Central question

> **Which kinds of distribution shift reduce a VLA policy's tolerance to inference delay, and under which behavioral demands?**

A complementary deployment question is:

> **Can standard native-latency robustness evaluations predict robustness once realistic inference delay is introduced?**

## Why this is the paper

Static OOD robustness and inference-delay robustness are usually evaluated separately. The paper tests their **interaction**.

A weak result is:

> OOD hurts, delay hurts, and OOD plus delay hurts more.

A stronger result is one or more of:

1. native-latency OOD success does not predict delayed OOD success;
2. perturbation families differ strongly in how much they reduce delay tolerance;
3. the same perturbation behaves differently across task-demand groups;
4. Naive async and RTC change ranking under OOD + delay;
5. executed action age explains failures that request latency alone does not.

## Primary model

```text
lerobot/pi05_libero_finetuned
```

Main evaluation override:

```text
policy.n_action_steps = 10
```

No additional VLA model is required for the primary paper.

## Primary execution methods

```text
Naive async
RTC
```

Ideal/blocking/horizon results from earlier work may be cited as preliminary context, but they are not part of the new critical-path factorial.

## Task-demand taxonomy

This is **our experimental taxonomy**, not an official LIBERO taxonomy.

| Display label | Interpretation | Base task |
|---|---|---|
| **Single-stage transport** | relatively short pick-and-place dominated by transport between grasp and placement | `libero_spatial:2` |
| **Articulated/contact-rich** | alignment/contact with an articulated object is central | `libero_goal:0` |
| **Multi-stage/sequential** | multiple ordered subgoals can accumulate errors | `libero_10:2` |

Exact standard-LIBERO task names:

```text
libero_spatial:2
pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate

libero_goal:0
open_the_middle_drawer_of_the_cabinet

libero_10:2
KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it
```

## Perturbation taxonomy

LIBERO-Plus provides seven perturbation dimensions. We retain those dimensions and introduce an internal mechanism grouping.

| LIBERO-Plus perturbation | Internal mechanism group | Intended interpretation |
|---|---|---|
| Object layout | **Trajectory adaptation** | changed task geometry may require a different trajectory |
| Robot initial state | **Trajectory adaptation** | changed manipulator start configuration requires adaptation |
| Camera viewpoint | **Perceptual localization** | changed viewpoint stresses spatial localization |
| Sensor noise | **Perceptual localization** | degraded observations stress localization/perception |
| Lighting | **Appearance invariance** | task geometry is largely preserved while appearance changes |
| Background texture | **Appearance invariance** | irrelevant scene/surface appearance changes |
| Language instruction | **Semantic grounding** | alternative instruction wording stresses language-conditioned grounding |

Use the exact four mechanism labels:

```text
Trajectory adaptation
Perceptual localization
Appearance invariance
Semantic grounding
```

## Hypotheses

### H1 — OOD × delay interaction

Distribution shift changes the marginal effect of inference delay:

```text
I =
  [S(OOD, high) - S(OOD, low)]
  -
  [S(ID, high) - S(ID, low)]
```

A negative `I` means OOD reduces delay tolerance.

### H2 — Perturbation mechanism

The interaction magnitude differs across perturbation-mechanism groups.

### H3 — Behavioral demand

The same perturbation can interact differently with delay on Single-stage transport, Articulated/contact-rich, and Multi-stage/sequential tasks.

### H4 — Execution method

Naive async and RTC can exhibit different OOD × delay interactions and may change ranking under OOD + delay.

### H5 — Temporal mechanism

Executed action age and queue behavior can help explain interaction patterns that are not visible from request latency alone.

H5 is mechanism analysis, not a separate headline contribution.

## Scope

### Required

- one π0.5 checkpoint;
- three base tasks;
- all seven LIBERO-Plus perturbation families;
- ID-only latency calibration;
- Native vs Native + `d*`;
- Naive async vs RTC;
- action provenance and age;
- complete exploratory reporting;
- held-out confirmation of selected candidate effects if time permits.

### Not required

- phase-conditioned interventions;
- dynamic target movement;
- VLASH;
- SmolVLA;
- streaming/corrective methods;
- additional model training;
- hardware robot validation.

## Main contribution

A controlled evaluation showing **how robustness to distribution shift changes once asynchronous inference delay is introduced**, organized by:

1. perturbation mechanism;
2. manipulation behavioral demand;
3. execution method.

Action-level provenance provides an explanatory temporal measurement layer.

## Explicit non-claims

Do not claim:

- a new execution algorithm;
- universal robustness rankings;
- hardware validity;
- safety guarantees;
- causal mechanisms from action-age correlation alone;
- that every OOD perturbation amplifies delay;
- that the internal taxonomy is a canonical robotics taxonomy.
