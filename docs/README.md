# OOD × Delay VLA Paper — Active Specification

This directory is the **clean active specification** for the paper.

The previous calendar-based files (`DAYS_1_3_SPEC.md`, `DAYS_4_8_SPEC.md`, `WEEK_2_SPEC.md`, `WEEK_3_SPEC.md`, `WEEK_4_SPEC.md`) are intentionally **not part of this pack**. The previous version manifest, cross-model baseline audit, and redundant experiment matrix are also removed.

Historical baseline results may still be used as background evidence, but they do not control the new experiment plan.

## Active scientific question

> **Which kinds of distribution shift reduce a VLA policy's tolerance to inference delay, and under which behavioral demands?**

A second question asks whether the answer changes between **Naive async** and **RTC**.

## Active model and methods

```text
Model:
    lerobot/pi05_libero_finetuned

Evaluation action horizon:
    n_action_steps = 25

Execution methods:
    Naive async
    RTC
```

`n_action_steps=25` is the frozen revised evaluation setting for Stages 1 and 2. It was selected from ID-only Stage 0 evidence and must not be changed in response to OOD outcomes.

## Canonical analysis taxonomy

### Task-demand groups

1. **Single-stage transport**
2. **Articulated/contact-rich**
3. **Multi-stage/sequential**

### Perturbation-mechanism groups

1. **Trajectory adaptation**
   - Object layout
   - Robot initial state
2. **Perceptual localization**
   - Camera viewpoint
   - Sensor noise
3. **Appearance invariance**
   - Lighting
   - Background texture
4. **Semantic grounding**
   - Language instruction

The seven perturbation families are LIBERO-Plus categories. The four mechanism groups and three task-demand groups are **our analysis taxonomy**.

## Execution order

### Stage 0 — ID-only latency calibration

Run:

```text
3 tasks
× 2 methods
× 8 added delays [0,100,200,300,400,500,600,700 ms]
× 2 seeds
= 96 episodes
```

Output:

```text
selected_high_delay.json
```

This freezes `d*` **without using OOD outcomes**.

### Stage 1 — broad OOD × delay screen

New OOD runs:

```text
3 tasks
× 7 perturbation families
× 2 delays [Native, Native + d*]
× 2 methods
× 5 seeds
= 420 new OOD episodes
```

The Stage 1 analysis also reuses 24 matching ID low/high episodes from Stage 0:

```text
420 OOD + 60 ID = 480 analysis episodes
24 ID episodes reused from Stage 0 + 36 new ID episodes
```

Total unique Stage 0 + Stage 1 compute:

```text
96 + 168 = 264 episodes
```

### Stage 2 — confirmatory follow-up

Only after Stage 1 is complete:

- apply the frozen selection rule;
- choose the strongest eligible candidate interactions;
- run **new held-out seeds**;
- do not change `d*`, tasks, taxonomy, or selected OOD variants after inspecting confirmatory outcomes.

See `STAGE_2_CONFIRMATORY_FOLLOWUP.md`.

## Files

| File | Purpose |
|---|---|
| `RESEARCH_CONTEXT.md` | current question, hypotheses, taxonomy, scope |
| `STAGE_0_LATENCY_CALIBRATION.md` | exact latency calibration runs and `d*` rule |
| `STAGE_1_EXPLORATORY_SCREEN.md` | exact 480-episode analysis plan across 96 condition blocks |
| `STAGE_2_CONFIRMATORY_FOLLOWUP.md` | predefined follow-up rule after exploratory screening |
| `METRICS_AND_LOGGING.md` | canonical timing, provenance, metrics, statistics |
| `PAPER_OUTLINE.md` | paper structure and allowable claims |
| `IMPLEMENTATION_STATUS.md` | active checklist |
| `DECISIONS.md` | frozen design decisions |
| `KNOWN_ISSUES.md` | current risks and mitigation |

## Explicitly out of scope for the critical path

Do not add these before Stage 0 and Stage 1 are complete:

```text
phase-conditioned delay experiments
dynamic target displacement
VLASH
SmolVLA
OpenVLA-OFT
FASTER
Reflex
VLA-Corrector
new training or fine-tuning
horizon sweeps
```

They may be reconsidered only after the primary OOD × delay result is known.

## Runtime expectation with two GPUs

Assuming roughly 3–5 minutes per episode and one independent worker per GPU:

```text
Stage 0: ~2.4–4.0 hours pure episode time
Stage 1: ~4.2–7.0 hours pure episode time
Combined: ~6.6–11.0 hours pure episode time
```

Budget additional time for environment startup, compilation, failed-run recovery, and analysis generation.

## Source anchors

- Official LIBERO task map:
  `https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/libero/libero/benchmark/libero_suite_task_map.py`
- Official LIBERO-Plus:
  `https://github.com/sylvestf/LIBERO-plus`
- Official LIBERO-Plus task classification:
  `https://github.com/sylvestf/LIBERO-plus/blob/main/libero/libero/benchmark/task_classification.json`
- LeRobot LIBERO evaluation:
  `https://huggingface.co/docs/lerobot/libero`
