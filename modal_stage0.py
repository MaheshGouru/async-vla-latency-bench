"""Minimal Modal deployment for the frozen Stage 0 latency calibration."""

from pathlib import Path

import modal


LEROBOT_COMMIT = "2aba372b4e217cc47db28e0f836859b20d1456c9"
VOLUME_NAME = "async-vla-benchmark-outputs"
VOLUME_ROOT = Path("/data/outputs")
STAGE0_OUTPUT_PATH = VOLUME_ROOT / "stage0"
REFINEMENT_OUTPUT_PATH = VOLUME_ROOT / "stage0_refinement_25_75"
CONFIG_PATH = Path(
    "/root/async-vla-latency-bench/async_vla_benchmark/configs/"
    "stage0_latency_calibration.yaml"
)

image = modal.Image.from_dockerfile(
    Path(__file__).parent / "Dockerfile.modal",
    build_args={"LEROBOT_COMMIT": LEROBOT_COMMIT},
).add_local_dir(
    "async_vla_benchmark/configs",
    remote_path="/root/async-vla-latency-bench/async_vla_benchmark/configs",
)

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App("async-vla-stage0-calibration", image=image)


def _run_script(argv: list[str]) -> int:
    import subprocess
    import sys

    command = [sys.executable, "-m", *argv]
    print(f"running: {' '.join(command)}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{argv[0]} exited with code {result.returncode}")
    return result.returncode


@app.function(
    gpu="A100-40GB",
    volumes={str(VOLUME_ROOT): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=12 * 60 * 60,
)
def run_stage0(
    tasks: str = "",
    methods: str = "",
    delays: str = "",
    seeds: str = "",
) -> int:
    command = [
        "async_vla_benchmark.scripts.run_stage0",
        "--config",
        str(CONFIG_PATH),
        "--output-dir",
        str(STAGE0_OUTPUT_PATH),
        "--resume",
    ]
    for value in tasks.split(",") if tasks else ():
        command.extend(["--task", value.strip()])
    for value in methods.split(",") if methods else ():
        command.extend(["--method", value.strip()])
    for value in delays.split(",") if delays else ():
        command.extend(["--added-delay-ms", value.strip()])
    for value in seeds.split(",") if seeds else ():
        command.extend(["--seed", value.strip()])
    try:
        return _run_script(command)
    finally:
        # Preserve every completed episode even if a later cell fails validation.
        volume.commit()


@app.function(
    gpu="A100-40GB",
    volumes={str(VOLUME_ROOT): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=6 * 60 * 60,
)
def run_stage0_refinement() -> int:
    command = [
        "async_vla_benchmark.scripts.run_stage0",
        "--config",
        str(CONFIG_PATH),
        "--refinement-25-75",
        "--output-dir",
        str(REFINEMENT_OUTPUT_PATH),
        "--base-output-dir",
        str(STAGE0_OUTPUT_PATH),
        "--resume",
    ]
    try:
        return _run_script(command)
    finally:
        volume.commit()


@app.function(
    volumes={str(VOLUME_ROOT): volume},
    timeout=30 * 60,
)
def analyze_stage0(allow_partial: bool = False) -> int:
    command = [
        "async_vla_benchmark.scripts.analyze_stage0",
        "--config",
        str(CONFIG_PATH),
        "--output-dir",
        str(STAGE0_OUTPUT_PATH),
    ]
    if allow_partial:
        command.append("--allow-partial")
    try:
        return _run_script(command)
    finally:
        volume.commit()


@app.local_entrypoint()
def main(
    command: str,
    tasks: str = "",
    methods: str = "",
    delays: str = "",
    seeds: str = "",
    allow_partial: bool = False,
    call_id: str = "",
) -> None:
    if command == "status":
        if not call_id:
            raise ValueError("--call-id is required for status")
        try:
            result = modal.FunctionCall.from_id(call_id).get(timeout=5)
        except TimeoutError:
            print(f"status=running; call_id={call_id}")
            return
        print(f"result={result}")
        return
    if command == "run":
        call = run_stage0.spawn(tasks, methods, delays, seeds)
    elif command == "refine":
        call = run_stage0_refinement.spawn()
    elif command == "analyze":
        call = analyze_stage0.spawn(allow_partial)
    else:
        raise ValueError("unknown command; choose run/refine/analyze/status")
    print(f"dispatched {command}; call_id={call.object_id}")
    print(
        "poll with: modal run modal_stage0.py::main --command status "
        f"--call-id {call.object_id}"
    )
