"""Modal deployment for the async-vla-latency-bench Days 1-3 pipeline.

Edit the *COMMIT constants below, then deploy with:

    modal deploy modal_app.py

Run a pipeline step from your local machine with:

    modal run modal_app.py::main --command select
    modal run modal_app.py::main --command profile
    modal run modal_app.py::main --command run --experiment core
    modal run modal_app.py::main --command validate
    modal run modal_app.py::main --command figures

Prerequisites:
- A Modal account and the `modal` Python package installed locally.
- A Modal Secret named `hf-token` containing `HF_TOKEN=<your HuggingFace token>`.
- Pinned LeRobot / robosuite / LIBERO commits set below.
"""

from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Pin these before deploying. Image rebuild is required when they change.
# ---------------------------------------------------------------------------
LEROOT_COMMIT = "main"          # e.g. "a1b2c3d"
ROBOSUITE_COMMIT = "master"     # e.g. "v1.4.1"
LIBERO_COMMIT = "master"        # e.g. "v0.0.1"

VOLUME_NAME = "async-vla-benchmark-outputs"
MOUNT_PATH = Path("/data/outputs")
CONFIG_PATH = Path("/root/async-vla-latency-bench/async_vla_benchmark/configs/days1_3.yaml")

image = modal.Image.from_dockerfile(
    Path(__file__).parent / "Dockerfile.modal",
    build_args={
        "LEROBOT_COMMIT": LEROOT_COMMIT,
        "ROBOSUITE_COMMIT": ROBOSUITE_COMMIT,
        "LIBERO_COMMIT": LIBERO_COMMIT,
    },
)

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# Mount the local config directory so config edits do not require an image rebuild.
config_mount = modal.Mount.from_local_dir(
    "async_vla_benchmark/configs",
    remote_path="/root/async-vla-latency-bench/async_vla_benchmark/configs",
)

app = modal.App("async-vla-benchmark", image=image)


def _run_script(argv: list[str]):
    """Run a benchmark CLI script by name from the installed package."""
    import subprocess
    import sys

    cmd = [sys.executable, "-m"] + argv
    print(f"running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


@app.function(
    gpu="T4",
    volumes={str(MOUNT_PATH): volume},
    mounts=[config_mount],
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=20 * 60,
)
def inspect_setup():
    """Capture environment metadata to the Modal volume."""
    return _run_script(
        ["async_vla_benchmark.scripts.inspect_setup", "--output-dir", str(MOUNT_PATH)]
    )


@app.function(
    gpu="T4",
    volumes={str(MOUNT_PATH): volume},
    mounts=[config_mount],
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=60 * 60,
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
    gpu="T4",
    volumes={str(MOUNT_PATH): volume},
    mounts=[config_mount],
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
    gpu="T4",
    volumes={str(MOUNT_PATH): volume},
    mounts=[config_mount],
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
    gpu="T4",
    volumes={str(MOUNT_PATH): volume},
    mounts=[config_mount],
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
    gpu="T4",
    volumes={str(MOUNT_PATH): volume},
    mounts=[config_mount],
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


@app.local_entrypoint
def main(
    command: str,
    experiment: str = "core",
    tasks: str = "",
    warmup: int = 10,
    measured: int = 100,
):
    """Dispatch a benchmark pipeline step to Modal from your local machine."""
    if command == "inspect":
        inspect_setup.remote()
    elif command == "select":
        select_tasks.remote()
    elif command == "profile":
        profile_latency.remote(warmup, measured)
    elif command == "run":
        run_benchmark.remote(experiment, tasks)
    elif command == "validate":
        validate_results.remote()
    elif command == "figures":
        make_figures.remote()
    else:
        raise ValueError(
            f"unknown command {command}; choose inspect/select/profile/run/validate/figures"
        )
