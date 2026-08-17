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
4. Can the surviving object-layout signal generalize across tasks and layout variants?

## Primary model

```text
lerobot/pi05_libero_finetuned
```

## Core methods

```text
RTC
Naive async
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

## Completed post-Stage-1 findings

### Stage 2

At `+200 ms`, pooled ID success is `14/15` at each of `n_action_steps={20,25,30}`, versus `6/15` at 10 actions. The 10-action regime also exhibits 1385 queue-underrun/hold steps at +200 ms, while horizons 20, 25, and 30 have zero. Therefore the frozen `25/+200` Stage-1 operating point is locally stable rather than a knife-edge optimum.

### Stage 3

Most Stage-1 localized negative interactions do not replicate on held-out seeds. The surviving candidate is `long_stove_moka × object_layout`, whose interaction remains negative across the frozen horizon neighborhood: `I_20=-0.125`, `I_25=-0.250`, `I_30=-0.125`. The additional delay penalty is modest relative to the large OOD main effect.

### Stage 3B

Stage 3B completed the cross-task object-layout replication. `spatial_transport` has `I={0,0,0}` at horizons `{20,25,30}` and OOD success is 8/8 -> 8/8 at every horizon. `goal_drawer` has `I={+0.125,+0.125,0}` with OOD 8/8 -> 8/8 throughout. `long_stove_moka` remains the only negative task with `I={-0.125,-0.250,-0.125}`. Thus the object-layout × delay effect is task-dependent rather than family-wide in the evaluated set.

### Stage 3C

The reset-only audit failed closed: for every frozen OOD object-layout variant, requested initialization indices `1..7` resolved to `0`, yielding only one distinct OOD initialization state. Cross-initialization generalization is therefore not evaluable for these variants.

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

## Required next experiments

1. Stage 2 — RTC local operating-point sensitivity (complete)
2. Stage 3 — OOD × horizon confirmation (complete)
3. Stage 3B — targeted cross-task object-layout replication (complete)
4. Stage 3C — reset-only initialization diversity/determinism audit (complete; failed closed)
5. Experiment A — within-task `long_stove_moka` object-layout variant generalization (active)
6. Experiment B — additional multi-stage task object-layout generalization (conditional)

## Explicit non-claims

Do not claim:
- broad OOD amplification from Stage 1;
- a universal RTC threshold;
- that `n_action_steps` equals RTC formal execution horizon `s` unless audited;
- a new async algorithm;
- safety or hardware validity;
- universal superiority of any execution method.


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


Stage 3B:

```text
RTC
new OOD tasks = spatial_transport, goal_drawer
perturbation = object_layout
n_action_steps = 20,25,30
delay = Native,+200 ms
seeds = 14..21
initialization_index_or_id = libero_episode_index:0
new episodes = 144 (96 OOD + 48 spatial ID)
```

This is a post-Stage-3 targeted cross-task replication. It determines whether
the object-layout interaction is a family-level tendency across task demands or
a localized long-task result.



Stage 3C — reset-only initialization audit:

```text
3 tasks × ID/OOD × initialization indices 0..7 × 3 clean resets
= 144 reset/fingerprint operations; no policy rollouts
```

## Post-Stage-3C active follow-up

Experiment A is the required next experiment:

```text
task = long_stove_moka
task type = multi_stage_sequential
perturbation = Objects Layout
new variants = 3
RTC; n_action_steps=25
delay = Native,+200
seeds = 22..29
libero_episode_index=0
64 episodes
```

Experiment B is conditional on the frozen Experiment-A gate and, if dispatched, uses:

```text
task = LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket
task type = multi_stage_sequential
perturbation = Objects Layout
variants = 3
RTC; n_action_steps=25
delay = Native,+200
seeds = 30..37
libero_episode_index=0
64 episodes
```
