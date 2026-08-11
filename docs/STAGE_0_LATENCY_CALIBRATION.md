# Stage 0 Latency Calibration

## Purpose

Choose one high added-delay value, `d*`, using standard LIBERO only. OOD outcomes
must not influence this choice.

## Frozen matrix

```text
policy:  lerobot/pi05_libero_finetuned
actions: n_action_steps=10
tasks:   libero_spatial:2, libero_goal:0, libero_10:2
methods: naive_async, rtc
delays:  0, 100, 200, 300, 400, 500, 600, 700 ms
seeds:   0, 1
total:   3 x 2 x 8 x 2 = 96 episodes
```

Every live task name must exactly match the name frozen in
`async_vla_benchmark/configs/stage0_latency_calibration.yaml`.

## Delay selection

First retain task x method cells with at least one Native success across the two
seeds. Choose the smallest nonzero delay where pooled success over viable cells:

- drops by at least 20 percentage points from Native;
- remains at or above 25 percent; and
- includes at least one successful episode.

If no delay satisfies that rule, apply the fallback rules encoded and tested in
`async_vla_benchmark/benchmark/stage0.py`. Write the result to
`selected_high_delay.json`; Stage 1 must read that file instead of choosing its own
delay.

## Execution

```bash
python -m async_vla_benchmark.scripts.run_stage0 --manifest-only
python -m async_vla_benchmark.scripts.run_stage0 --resume
modal run --detach modal_stage0.py::main --command run
```

Stage 0 writes to `/data/outputs/stage0` on the existing Modal volume. The old
Days 1-3 artifacts remain under `/data/outputs` and are not overwritten.

## 25/50/75 ms refinement

The credit-conscious follow-up keeps the original Stage 0 frozen and evaluates
only the three task x method cells that were viable at Native latency:

```text
libero_goal:0  x naive_async
libero_goal:0  x rtc
libero_10:2    x naive_async
delays: 25, 50, 75 ms
seeds: 0, 1
total: 3 x 3 x 2 = 18 new episodes
```

The analysis reuses the original 0 and 100 ms boundary episodes and writes a
separate refined curve under `/data/outputs/stage0_refinement_25_75`.

```bash
python -m async_vla_benchmark.scripts.run_stage0 \
  --refinement-25-75 \
  --manifest-only

modal run --detach modal_stage0.py::main --command refine
```
