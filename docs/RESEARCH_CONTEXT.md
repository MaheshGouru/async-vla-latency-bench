# Research Context

## Working title

**Temporal Coverage Under Shift: Horizon–Latency Robustness of Asynchronous Vision-Language-Action Policies**

## Current empirical situation

Stage 1 did not support a general claim that LIBERO-Plus OOD shifts amplify
sensitivity to +200 ms delay.

```text
ID:  60.0% -> 56.7%
OOD: 60.0% -> 58.1%
I ≈ +1.4 pp
```

However:
- RTC substantially outperformed Naive async at `n_action_steps=25`;
- the earlier `n_action_steps=10` configuration showed RTC collapse under small
  added delay;
- localized RTC OOD interactions appeared on selected task/perturbation cells.

## Primary research question

> **How does temporal action coverage determine asynchronous VLA robustness to
> inference delay, and do distribution shifts move that robustness boundary?**

Secondary questions:
1. Is the 10-action versus 25-action difference explained by a horizon–latency
   operating envelope?
2. Does delay normalized by configured action coverage organize success better
   than milliseconds alone?
3. Do selected OOD perturbations shrink/shift that envelope?
4. Does VLASH show the same phenomenon if a fair official integration is feasible?

## Primary model

```text
lerobot/pi05_libero_finetuned
```

## Core methods

```text
RTC
Naive async
```

Conditional:
```text
VLASH
```

## Task-demand taxonomy

| Display label | Base task |
|---|---|
| Single-stage transport | `libero_spatial:2` |
| Articulated/contact-rich | `libero_goal:0` |
| Multi-stage/sequential | `libero_10:2` |

These labels are our analysis taxonomy.

## Perturbation mechanism taxonomy

| Perturbation | Internal mechanism group |
|---|---|
| Object layout | Trajectory adaptation |
| Robot initial state | Trajectory adaptation |
| Camera viewpoint | Perceptual localization |
| Sensor noise | Perceptual localization |
| Lighting | Appearance invariance |
| Background texture | Appearance invariance |
| Language instruction | Semantic grounding |

LIBERO-Plus perturbation families are official benchmark categories; the four
mechanism groups are ours.

## Completed Stage 1 findings

Broad result:
> No broad evidence that OOD amplifies +200 ms delay at the 25-action operating point.

Prespecified tied follow-up families:
```text
Object layout
Robot initial state
Lighting
```

Secondary post-hoc signal:
```text
Goal drawer × Sensor noise × RTC
```

## New hypotheses

### H1 — Horizon × latency envelope
RTC success depends strongly on the joint relationship between configured action
coverage and inference delay.

### H2 — Normalized temporal coverage
Effective delay in control steps relative to configured action coverage organizes
outcomes better than milliseconds alone.

### H3 — OOD boundary shift
Selected OOD perturbations can move the horizon–latency boundary even though the
aggregate Stage 1 interaction at 25 actions is near zero.

### H4 — Method dependence
The horizon/latency relationship differs between RTC and a naive asynchronous queue.

### H5 — Optional cross-method validation
If official VLASH integration is feasible, localized effects may differ across
modern asynchronous alignment strategies.

## Required next experiments

1. Stage 2 — RTC local operating-point sensitivity
2. Stage 3 — OOD × horizon confirmation
3. Stage 4 — conditional VLASH subset

## Explicit non-claims

Do not claim:
- broad OOD amplification from Stage 1;
- a universal RTC threshold;
- that `n_action_steps` equals RTC formal execution horizon `s` unless audited;
- a new async algorithm;
- safety or hardware validity;
- universal superiority of RTC/VLASH.


## Frozen post-Stage-1 sensitivity design

Stage 2:

```text
RTC
n_action_steps = 10,15,20,25,30,35
delay = Native,+100,+200,+300 ms
seeds = 5,6,7,8,9
```

Native at every horizon distinguishes an action-coverage main effect from
sensitivity to injected delay.

Stage 3:

```text
n_action_steps = 20,25,30
delay = Native,+200 ms
seeds = 14..21
```

The Stage 3 horizon set is frozen before Stage 2 and is not selected after
inspecting Stage 2.
