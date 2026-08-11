# Research Context

## Working title

Robustness Under Delay: OOD x Inference-Latency Interactions in
Vision-Language-Action Policies

## Central question

Which kinds of distribution shift reduce a VLA policy's tolerance to inference
delay, and under which behavioral demands?

The completed Days 1-3 experiment established the execution harness and measured
the latency regime. Its ideal-sync, blocking-sync, and horizon-sweep results are
historical context, not the new critical-path factorial.

## Active stage

Stage 0 is an in-distribution-only latency calibration. It uses the frozen
`lerobot/pi05_libero_finetuned` checkpoint with `n_action_steps=10` and compares:

- `naive_async`
- `rtc`

The exact base tasks are:

- `libero_spatial:2` - Single-stage transport
- `libero_goal:0` - Articulated/contact-rich
- `libero_10:2` - Multi-stage/sequential

Stage 0 tests 0 through 700 ms of added delay in 100 ms increments with seeds 0
and 1. The 96 ID episodes select one non-saturating high delay, `d*`, without
using any OOD outcomes.

## Paper path

Stage 1 will cross Native versus Native + `d*` with the seven LIBERO-Plus
perturbation families under Naive async and RTC. Stage 2 may confirm selected
interactions on held-out seeds.

The stronger target result is not merely that OOD and delay both hurt. It is that
native-latency OOD performance may fail to predict delayed OOD performance, or
that perturbation families and behavioral demands differ in how much they reduce
delay tolerance.

## Scope boundary

The current implementation task is Stage 0 only. Do not add OOD execution,
phase-conditioned interventions, dynamic target movement, new policies, training,
VLASH, FASTER, or other execution methods before Stage 0 is complete and `d*` is
frozen.
