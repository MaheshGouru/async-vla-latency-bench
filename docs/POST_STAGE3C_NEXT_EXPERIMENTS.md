# Post-Initialization-State Audit Experiment Plan — Updated After Object-Layout and Multi-Stage Task Generalization

## Completed follow-ups

### Object-Layout Generalization — COMPLETE

`long_stove_moka`, three new Objects-Layout variants, RTC, `n_action_steps=25`, Native/+200 ms, seeds `22..29`, initialization index 0, 64 valid analysis episodes.

Result:

```text
I = -0.375, +0.125, -0.125
negative in 2/3 new layouts
mean I = -0.125
```

Interpretation: the negative effect is not unique to the original layout, but is heterogeneous across layouts.

### Multi-Stage Task Generalization — COMPLETE

`LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket`, three Objects-Layout variants, RTC, `n_action_steps=25`, Native/+200 ms, seeds `30..37`, initialization index 0, 64 analysis episodes.

Result:

```text
I = -0.375, +0.250, +0.625
negative in 1/3 layouts
mean I = +0.167
```

Interpretation: the negative `long_stove_moka` pattern does not consistently transfer to a second multi-stage task.

## Cross-Policy OpenVLA-OFT Diagnostic — COMPLETE preliminary/native-stack diagnostic

At OpenVLA-OFT coverage 8:

```text
spatial_transport: I=+0.250; ID 8/8->6/8; OOD 8/8->8/8
long_stove_moka:   I=+0.125; ID 1/8->0/8; OOD 0/8->0/8
```

The long task is floor-limited, and coverage 8 was not calibrated for asynchronous latency.

## Final active experiment

### High-Power OOD–Delay Replication — high-power Held-Out OOD–Delay Horizon Confirmation / Held-Out Object-Layout Cross-Task Replication replication

Run exactly:

```text
STAGE_3_NEW_HIGH_POWER_REPLICATION.md
```

The experiment reruns the six unique task × perturbation pairs represented by
Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication, including the Held-Out OOD–Delay Horizon Confirmation post-hoc sensor-noise condition.

```text
π0.5 + RTC
horizons = 20,25,30
delay = Native,+200 ms
fresh seeds = 46..109
64 seeds/cell
3,456 new physical episodes with shared ID controls
```

No old Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication episode outcomes are pooled into the primary estimates.

OpenVLA-OFT Temporal-Coverage Calibration is canceled before execution. The remaining compute budget
is dedicated to reducing uncertainty in the existing interaction matrix.
