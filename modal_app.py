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
LEROOT_COMMIT = "2aba372b4e217cc47db28e0f836859b20d1456c9"  # resolved from main on 2026-07-30

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
    gpu="A100-40GB",
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
    gpu="A100-40GB",
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
    gpu="A100-40GB",
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
    gpu="A100-40GB",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=6 * 60 * 60,
)
def run_benchmark(
    experiment: str = "core",
    tasks: str = "",
    seeds: str = "",
    strategy: str = "",
    latency_profile: str = "",
):
    """Run the full core or horizon_sweep experiment on a GPU worker.

    `tasks` is a comma-separated list of "suite:task_id" strings.
    If empty, the selected-tasks manifest on the volume is used.
    `seeds` is a comma-separated list of ints. If empty, the experiment's
    default seeds are used.
    `strategy`/`latency_profile` filter the expanded plan to a single value
    each (e.g. "rtc" / "native"). If empty, all values are included.
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
    if seeds:
        for seed in seeds.split(","):
            cmd.extend(["--seed", seed.strip()])
    if strategy:
        cmd.extend(["--strategy", strategy])
    if latency_profile:
        cmd.extend(["--latency-profile", latency_profile])
    return _run_script(cmd)


@app.function(
    gpu="A100-40GB",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=20 * 60,
)
def diagnose_observation(suite: str = "libero_spatial", task_id: int = 0, seed: int = 0):
    """Dump raw observation structure, camera frames, and orientation-conversion checks."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.diagnose_observation",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(MOUNT_PATH),
            "--suite",
            suite,
            "--task-id",
            str(task_id),
            "--seed",
            str(seed),
        ]
    )


@app.function(
    gpu="A100-40GB",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=20 * 60,
)
def diagnose_action_scale(suite: str = "libero_spatial", task_id: int = 0, seed: int = 0):
    """Check the postprocessor's action un-normalization and the real physical
    displacement one predicted action produces, against the controller's configured scale."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.diagnose_action_scale",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(MOUNT_PATH),
            "--suite",
            suite,
            "--task-id",
            str(task_id),
            "--seed",
            str(seed),
        ]
    )


@app.function(
    gpu="A100-40GB",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=20 * 60,
)
def diagnose_raw_action_scale(
    suite: str = "libero_spatial", task_id: int = 0, seed: int = 0, repeat: int = 5
):
    """Bypass the policy and apply hand-crafted actions directly to the env, to
    isolate whether an action-scale mismatch is in our pipeline or the env/controller."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.diagnose_raw_action_scale",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(MOUNT_PATH),
            "--suite",
            suite,
            "--task-id",
            str(task_id),
            "--seed",
            str(seed),
            "--repeat",
            str(repeat),
        ]
    )


@app.function(
    gpu="A100-40GB",
    volumes={str(MOUNT_PATH): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=20 * 60,
)
def run_single_episode(suite: str = "libero_spatial", task_id: int = 0, seed: int = 0):
    """Run exactly one ideal-sync episode, for quickly checking whether a pipeline
    change actually moves task success (without re-running the full sweep)."""
    return _run_script(
        [
            "async_vla_benchmark.scripts.run_single_episode",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(MOUNT_PATH),
            "--suite",
            suite,
            "--task-id",
            str(task_id),
            "--seed",
            str(seed),
        ]
    )


@app.function(
    gpu="A100-40GB",
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
    gpu="A100-40GB",
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
    seeds: str = "",
    strategy: str = "",
    latency_profile: str = "",
    warmup: int = 10,
    measured: int = 100,
    call_id: str = "",
    suite: str = "libero_spatial",
    task_id: int = 0,
    seed: int = 0,
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
        "run": lambda: run_benchmark.spawn(experiment, tasks, seeds, strategy, latency_profile),
        "validate": lambda: validate_results.spawn(),
        "figures": lambda: make_figures.spawn(),
        "diagnose": lambda: diagnose_observation.spawn(suite, task_id, seed),
        "diagnose_scale": lambda: diagnose_action_scale.spawn(suite, task_id, seed),
        "diagnose_raw_scale": lambda: diagnose_raw_action_scale.spawn(suite, task_id, seed),
    }
    if command == "status":
        if not call_id:
            raise ValueError("--call-id is required for the status command")
        result = modal.FunctionCall.from_id(call_id).get(timeout=5)
        print(f"result={result}")
        return
    if command not in dispatch:
        raise ValueError(
            "unknown command "
            f"{command}; choose inspect/select/profile/run/validate/figures/"
            "diagnose/diagnose_scale/diagnose_raw_scale/status"
        )
    call = dispatch[command]()
    print(f"dispatched {command}; call_id={call.object_id}")
    print(f"poll with: modal run modal_app.py::main --command status --call-id {call.object_id}")
