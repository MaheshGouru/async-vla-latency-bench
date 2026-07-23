"""Modal deployment for the async-vla-latency-bench Days 1-3 pipeline.

Edit the *COMMIT constants below, then deploy with:

    modal deploy modal_app.py

Dispatch a pipeline step from your local machine with (this only submits the
job and returns a call_id immediately; it does not wait for it to finish):

    modal run modal_app.py::main --command select
    modal run modal_app.py::main --command profile
    modal run modal_app.py::main --command run --experiment core
    modal run modal_app.py::main --command validate
    modal run modal_app.py::main --command figures

Then poll for the result with:

    modal run modal_app.py::main --command status --call-id <call_id>

Prerequisites:
- A Modal account and the `modal` Python package installed locally.
- A Modal Secret named `hf-token` containing `HF_TOKEN=<your HuggingFace token>`.
- Pinned LeRobot commit set below. robosuite/mujoco/bddl come from LeRobot's
  own `[libero]` extra (the `hf-libero` PyPI package) and are not pinned here.
"""

from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Pin this before deploying. Image rebuild is required when it changes.
# ---------------------------------------------------------------------------
LEROOT_COMMIT = "main"          # e.g. "a1b2c3d"

VOLUME_NAME = "async-vla-benchmark-outputs"
MOUNT_PATH = Path("/data/outputs")
CONFIG_PATH = Path("/root/async-vla-latency-bench/async_vla_benchmark/configs/days1_3.yaml")

image = modal.Image.from_dockerfile(
    Path(__file__).parent / "Dockerfile.modal",
    build_args={
        "LEROBOT_COMMIT": LEROOT_COMMIT,
    },
).add_local_dir(
    "async_vla_benchmark/configs",
    remote_path="/root/async-vla-latency-bench/async_vla_benchmark/configs",
)

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

app = modal.App("async-vla-benchmark", image=image)


def _run_script(argv: list[str]):
    """Run a benchmark CLI script by name from the installed package."""
    import subprocess
    import sys

    cmd = [sys.executable, "-m"] + argv
    print(f"running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    return result.returncode


@app.function(
    gpu="A10G",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=20 * 60,
)
def inspect_setup():
    """Capture environment metadata to the Modal volume."""
    return _run_script(
        ["async_vla_benchmark.scripts.inspect_setup", "--output-dir", str(MOUNT_PATH)]
    )


@app.function(
    gpu="A10G",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=4 * 60 * 60,
)
def select_tasks():
    """Run ideal-sync episodes and write selected_tasks.json to the volume."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.select_tasks",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(MOUNT_PATH),
        ]
    )


@app.function(
    gpu="A10G",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=60 * 60,
)
def profile_latency(warmup: int = 10, measured: int = 100):
    """Profile native request latency on a GPU worker."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.profile_latency",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(MOUNT_PATH),
            "--warmup-requests",
            str(warmup),
            "--measured-requests",
            str(measured),
        ]
    )


@app.function(
    gpu="A10G",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=2 * 60 * 60,
)
def run_benchmark(experiment: str = "core", tasks: str = ""):
    """Run the full core or horizon_sweep experiment on a GPU worker.

    `tasks` is a comma-separated list of "suite:task_id" strings.
    If empty, the selected-tasks manifest on the volume is used.
    """
    cmd = [
        "async_vla_benchmark.scripts.run_benchmark",
        "--config",
        str(CONFIG_PATH),
        "--output-dir",
        str(MOUNT_PATH),
        "--experiment",
        experiment,
    ]
    if tasks:
        for task in tasks.split(","):
            cmd.extend(["--task", task.strip()])
    return _run_script(cmd)


@app.function(
    gpu="A10G",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=30 * 60,
)
def validate_results():
    """Validate all episode artifacts on the volume."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.validate_results",
            "--output-dir",
            str(MOUNT_PATH),
        ]
    )


@app.function(
    gpu="A10G",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=30 * 60,
)
def make_figures():
    """Generate aggregate figures from validated summaries."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.make_figures",
            "--output-dir",
            str(MOUNT_PATH),
        ]
    )


@app.local_entrypoint()
def main(
    command: str,
    experiment: str = "core",
    tasks: str = "",
    warmup: int = 10,
    measured: int = 100,
    call_id: str = "",
):
    """Dispatch a benchmark pipeline step to Modal from your local machine.

    Uses `.spawn()` rather than `.remote()` so the local process only needs to
    survive submitting the call, not the whole run: `.remote()` blocks on an
    open RPC for the entire remote execution, and a local process/session
    getting killed mid-wait cancels that RPC (and the remote job with it) even
    under `modal run --detach`. `.spawn()` returns a call_id immediately; poll
    it later with `--command status --call-id <id>` from a fresh short-lived
    process.
    """
    dispatch = {
        "inspect": lambda: inspect_setup.spawn(),
        "select": lambda: select_tasks.spawn(),
        "profile": lambda: profile_latency.spawn(warmup, measured),
        "run": lambda: run_benchmark.spawn(experiment, tasks),
        "validate": lambda: validate_results.spawn(),
        "figures": lambda: make_figures.spawn(),
    }
    if command == "status":
        if not call_id:
            raise ValueError("--call-id is required for the status command")
        result = modal.FunctionCall.from_id(call_id).get(timeout=5)
        print(f"result={result}")
        return
    if command not in dispatch:
        raise ValueError(
            f"unknown command {command}; choose inspect/select/profile/run/validate/figures/status"
        )
    call = dispatch[command]()
    print(f"dispatched {command}; call_id={call.object_id}")
    print(f"poll with: modal run modal_app.py::main --command status --call-id {call.object_id}")
