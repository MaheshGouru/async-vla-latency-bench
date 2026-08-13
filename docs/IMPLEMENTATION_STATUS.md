# Implementation Status

Last updated: 2026-08-11

## Completed prerequisite

Mathew's Days 1-3 run produced 222 validated episodes on Modal and established
the reusable discrete-event runner, request/action provenance, Naive async and RTC
adapters, result validation, and pinned pi0.5-LIBERO environment.

Those outputs remain historical evidence. They use task IDs 0/0/0 and do not
constitute the new Stage 0 calibration.

## Stage 0 calibration

Stage 0 - ID-only latency calibration

- [x] Pin LeRobot revision
- [x] Pin pi0.5 checkpoint revision
- [x] Freeze exact task IDs and names at 2/0/2
- [x] Freeze Naive async and RTC as the two methods
- [x] Freeze delays 0 through 700 ms in 100 ms increments
- [x] Freeze seeds 0 and 1
- [x] Generate the 96-episode manifest
- [x] Isolate Stage 0 outputs from Days 1-3 artifacts
- [x] Add task-name and experiment-matrix preflight assertions
- [x] Add Stage 0 result tables, figures, and frozen `d*` selection
- [x] Correct action-age aggregation to exclude source-less hold actions
- [x] Build the pinned CUDA/LeRobot/LIBERO Modal image
- [x] Validate the CUDA/EGL image and exact live task names on Modal
- [x] Run all 96 calibration episodes
- [x] Validate all 96 episode/request/action artifacts
- [x] Generate final calibration artifacts
- [x] Freeze `selected_high_delay.json` at `d*=100 ms`

All 96 manifest rows completed with valid episode, request, and action logs. The
low-delay results also exposed queue starvation in some Native cells; this is an
experimental outcome rather than a missing or malformed run.

## Stage 1 scaffolding

Stage 1 moves to LIBERO-Plus OOD x latency once Stage 0 has frozen `d*`.

- [x] Read Stage 0 `selected_high_delay.json` instead of selecting delay from OOD
- [x] Add frozen Stage 1 config for the 2/0/2 Stage 0 tasks
- [x] Cross the seven LIBERO-Plus perturbation families with Native and Native + `d*`
- [x] Restrict methods to Naive async and RTC
- [x] Reuse the existing discrete-event runner, policy wrapper, queue logic, RTC adapter, and validation
- [x] Add a LIBERO-Plus Modal entrypoint for manifest, dry-run, filtered, and resumable runs
- [ ] Run the Stage 1 manifest in the LIBERO-Plus image and verify category/task-id resolution
- [ ] Run Stage 1 episodes on Modal
- [ ] Aggregate Stage 1 summaries and generate paper-facing figures

## Active refinement

An 18-episode follow-up was submitted on 2026-08-11 for 25, 50, and 75 ms added
delay. It is restricted to the three task x method cells that had at least one
Native success:

```text
libero_goal:0 x naive_async
libero_goal:0 x rtc
libero_10:2   x naive_async
```

The refinement writes to `/data/outputs/stage0_refinement_25_75` and does not
modify the frozen 96-episode calibration. Raw exports and result archives are
intentionally ignored by Git and should be shared separately from the code PR.
