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

## Active next experiment

### Stage 5 — OpenVLA-OFT temporal-coverage calibration and conditional final replication

Run exactly `STAGE_5_OPENVLA_OFT_COVERAGE_CALIBRATION_AND_FINAL_REPLICATION.md`.

First audit whether the checkpoint can legitimately provide >8 future actions from one inference. Only if it can should a larger-coverage sweep be run. Coverage selection must use ID only. A final OOD × delay rerun uses fresh seeds `51..58` only after coverage is frozen.
