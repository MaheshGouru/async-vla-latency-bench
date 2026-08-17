# Post-Stage-3C Active Experiment Plan

Stage 3C established that the frozen LIBERO-Plus object-layout variants expose only one OOD initialization state, so cross-initialization generalization cannot be evaluated under the benchmark interface. Do not manufacture initialization diversity.

## Required next experiment

Run `EXPERIMENT_A_OBJECT_LAYOUT_VARIANT_GENERALIZATION.md`.

It tests whether the Stage-3 `long_stove_moka × object_layout` interaction persists across **three additional deterministically frozen object-layout variants of the same multi-stage task**.

Frozen execution: RTC, `n_action_steps=25`, delays `{Native,+200 ms}`, seeds `[22..29]`, `libero_episode_index=0`, 16 fresh ID + 48 OOD = **64 new episodes**, plus seed-999 smoke outside analysis.

## Conditional follow-up

Run `EXPERIMENT_B_ADDITIONAL_MULTI_STAGE_TASK_GENERALIZATION.md` only if Experiment A passes the frozen gate:

```text
>= 2/3 new variants have I < 0
AND mean I across the 3 variants < 0
AND no unresolved validation/provenance failure
```

Experiment B uses the frozen `libero_10` task `LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket`, three deterministically frozen object-layout variants, RTC, `n_action_steps=25`, delays `{Native,+200 ms}`, seeds `[30..37]`, initialization 0, and **64 new episodes**, plus seed-999 smoke outside analysis.

No other experiment is active.
