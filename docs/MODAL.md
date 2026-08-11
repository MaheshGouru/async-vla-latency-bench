# Running the Benchmark on Modal

## Active Stage 0 run

The narrowed ID-only latency calibration uses the minimal `modal_stage0.py` app:

```bash
modal run --detach modal_stage0.py::main --command run
```

Run the isolated 25/50/75 ms refinement on the native-viable cells:

```bash
modal run --detach modal_stage0.py::main --command refine
```

This dispatches 18 new A100 episodes and writes them to
`/data/outputs/stage0_refinement_25_75` without modifying the original Stage 0
results.

It submits 96 sequential A100 episodes and returns a call ID. Poll it with:

```bash
modal run modal_stage0.py::main --command status --call-id <call_id>
```

Stage 0 outputs are isolated at `/data/outputs/stage0` on the existing
`async-vla-benchmark-outputs` volume. The remaining commands below document the
completed Days 1-3 pipeline.

This repository includes a `modal_app.py` deployment that executes the Days 1–3
benchmark pipeline on GPU workers in the cloud. It persists outputs to a Modal
Volume mounted at `/data/outputs`.

## Files

- `modal_app.py` – Modal App with remote functions and a `local_entrypoint`.
- `Dockerfile.modal` – CUDA/EGL image with pinned LeRobot / robosuite / LIBERO installs.
- `pyproject.toml` – Installs the `async-vla_benchmark` package inside the image.

## One-time setup

1. Install Modal locally and authenticate:

```bash
pip install modal
modal setup
```

2. Create a HuggingFace token secret so the container can download the π0.5 checkpoint:

```bash
modal secret create hf-token HF_TOKEN=<your_hf_token>
```

3. Pin the commits / tags you want to use by editing `modal_app.py`:

```python
LEROOT_COMMIT = "abc1234"      # LeRobot git commit or tag
ROBOSUITE_COMMIT = "v1.4.1"    # robosuite git commit or tag
LIBERO_COMMIT = "v0.0.1"       # LIBERO git commit or tag
```

Also set `checkpoint_revision` and `dataset_revision` in
`async_vla_benchmark/configs/days1_3.yaml`.

## Deploy

```bash
modal deploy modal_app.py
```

The first deploy builds the Docker image; subsequent deploys with unchanged
commits will reuse the cached image.

## Run the pipeline

Modal `local_entrypoint` commands dispatch from your local machine to the cloud:

```bash
# Inspect the remote environment
modal run modal_app.py::main --command inspect

# Select viable tasks (writes selected_tasks.json to the volume)
modal run modal_app.py::main --command select

# Profile native request latency
modal run modal_app.py::main --command profile

# Run the core experiment
modal run modal_app.py::main --command run --experiment core

# Or run a subset for debugging
modal run modal_app.py::main --command run --experiment core \
  --tasks libero_spatial:0,libero_goal:0

# Run the horizon sweep
modal run modal_app.py::main --command run --experiment horizon_sweep

# Validate and generate figures
modal run modal_app.py::main --command validate
modal run modal_app.py::main --command figures
```

## Outputs

All outputs are written to the Modal Volume `async-vla-benchmark-outputs`. You
can inspect or download them with Modal's volume commands:

```bash
modal volume ls async-vla-benchmark-outputs
modal volume get async-vla-benchmark-outputs / /local/path
```

## Notes

- `modal_app.py` mounts `async_vla_benchmark/configs/` at runtime, so config
  changes do not require an image rebuild.
- GPU type is set to `T4` by default. For faster inference, change the `gpu=`
  argument in `modal_app.py` to `A10G` or `A100` before deploying.
- The Dockerfile installs LeRobot, robosuite, and LIBERO from git. If the
  package extras or repository names have changed, edit `Dockerfile.modal`
  accordingly.
