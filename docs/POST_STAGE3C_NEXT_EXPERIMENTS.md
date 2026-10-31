# Post-Stage-3C Experiment Plan — Updated After Experiments A and B

## Completed follow-ups

### Experiment A — COMPLETE

`long_stove_moka`, three new Objects-Layout variants, RTC, `n_action_steps=25`, Native/+200 ms, seeds `22..29`, initialization index 0, 64 valid analysis episodes.

Result:

```text
I = -0.375, +0.125, -0.125
negative in 2/3 new layouts
mean I = -0.125
```

Interpretation: the negative effect is not unique to the original layout, but is heterogeneous across layouts.

### Experiment B — COMPLETE

`LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket`, three Objects-Layout variants, RTC, `n_action_steps=25`, Native/+200 ms, seeds `30..37`, initialization index 0, 64 analysis episodes.

Result:

```text
I = -0.375, +0.250, +0.625
negative in 1/3 layouts
mean I = +0.167
```

Interpretation: the negative `long_stove_moka` pattern does not consistently transfer to a second multi-stage task.

## Stage 4 — COMPLETE preliminary/native-stack diagnostic

At OpenVLA-OFT coverage 8:

```text
spatial_transport: I=+0.250; ID 8/8->6/8; OOD 8/8->8/8
long_stove_moka:   I=+0.125; ID 1/8->0/8; OOD 0/8->0/8
```

The long task is floor-limited, and coverage 8 was not calibrated for asynchronous latency.

## Final active experiment

### Stage 3 New — high-power Stage 3 / Stage 3B replication

Run exactly:

```text
STAGE_3_NEW_HIGH_POWER_REPLICATION.md
```

The experiment reruns the six unique task × perturbation pairs represented by
Stage 3 and Stage 3B, including the Stage-3 post-hoc sensor-noise condition.

```text
π0.5 + RTC
horizons = 20,25,30
delay = Native,+200 ms
fresh seeds = 46..109
64 seeds/cell
3,456 new physical episodes with shared ID controls
```

No old Stage 3/3B episode outcomes are pooled into the primary estimates.

Stage 5 OpenVLA-OFT is canceled before execution. The remaining compute budget
is dedicated to reducing uncertainty in the existing interaction matrix.
