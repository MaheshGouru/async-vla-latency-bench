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

## Active next experiment

### Stage 4 — second-policy OpenVLA-OFT replication

Run exactly `STAGE_4_SECOND_POLICY_OPENVLA_OFT.md`.

```text
policy = moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10
tasks = spatial_transport, long_stove_moka
perturbation = Objects Layout
exact OOD variants = c1773/add_15 and c1941/add_25
execution = naive async, not RTC
native chunk = 8 actions
request threshold = 4
delay = Native,+200 ms
seeds = 38..45
libero_episode_index = 0
64 analysis episodes
4 seed-999 smoke episodes excluded from analysis
```

Do not add more π0.5 tasks before Stage 4 unless Stage 4 is infeasible for implementation reasons. The highest-value remaining question is cross-policy external validity.
