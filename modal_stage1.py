"""Modal deployment for Stage 1 LIBERO-Plus OOD x latency runs.

Examples:

    modal run modal_stage1.py::main --command manifest
    modal run --detach modal_stage1.py::main --command run --perturbations camera_viewpoints
    modal run modal_stage1.py::main --command status --call-id <call_id>
"""

from pathlib import Path

import modal


LEROBOT_COMMIT = "2aba372b4e217cc47db28e0f836859b20d1456c9"
LIBERO_PLUS_SHA = "4976dc3"
VOLUME_NAME = "async-vla-benchmark-outputs"
VOLUME_ROOT = Path("/data/outputs")
STAGE1_OUTPUT_PATH = VOLUME_ROOT / "stage1_libero_plus"
CONFIG_PATH = Path(
    "/root/async-vla-latency-bench/async_vla_benchmark/configs/"
    "stage1_libero_plus.yaml"
)
DELAY_SELECTION_PATH = VOLUME_ROOT / "stage0" / "selected_high_delay.json"

image = modal.Image.from_dockerfile(
    Path(__file__).parent / "Dockerfile.modal.libero_plus",
    build_args={
        "LEROBOT_COMMIT": LEROBOT_COMMIT,
        "LIBERO_PLUS_SHA": LIBERO_PLUS_SHA,
    },
).add_local_dir(
    "async_vla_benchmark/configs",
    remote_path="/root/async-vla-latency-bench/async_vla_benchmark/configs",
)

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App("async-vla-stage1-libero-plus", image=image)


def _run_script(argv: list[str]) -> int:
    import subprocess
    import sys

    command = [sys.executable, "-m", *argv]
    print(f"running: {' '.join(command)}")
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    combined = result.stdout + "\n" + result.stderr
    output_tail = combined[-6000:]
    if output_tail:
        print("--- subprocess output tail ---")
        print(output_tail)
    if result.returncode != 0:
        raise RuntimeError(
            f"{argv[0]} exited with code {result.returncode}\n"
            f"--- subprocess output tail ---\n{output_tail}"
        )
    return result.returncode


def _base_command() -> list[str]:
    return [
        "async_vla_benchmark.scripts.run_stage1",
        "--config",
        str(CONFIG_PATH),
        "--output-dir",
        str(STAGE1_OUTPUT_PATH),
        "--stage0-delay-selection-file",
        str(DELAY_SELECTION_PATH),
    ]


def _append_filters(
    command: list[str],
    *,
    tasks: str = "",
    methods: str = "",
    perturbations: str = "",
    latency_conditions: str = "",
    seeds: str = "",
) -> list[str]:
    for value in tasks.split(",") if tasks else ():
        command.extend(["--task", value.strip()])
    for value in methods.split(",") if methods else ():
        command.extend(["--method", value.strip()])
    for value in perturbations.split(",") if perturbations else ():
        command.extend(["--perturbation", value.strip()])
    for value in latency_conditions.split(",") if latency_conditions else ():
        command.extend(["--latency-condition", value.strip()])
    for value in seeds.split(",") if seeds else ():
        command.extend(["--seed", value.strip()])
    return command


@app.function(
    volumes={str(VOLUME_ROOT): volume},
    timeout=30 * 60,
)
def write_manifest() -> int:
    command = _base_command()
    command.append("--manifest-only")
    try:
        return _run_script(command)
    finally:
        volume.commit()


@app.function(
    volumes={str(VOLUME_ROOT): volume},
    timeout=30 * 60,
)
def dry_run(
    tasks: str = "",
    methods: str = "",
    perturbations: str = "",
    latency_conditions: str = "",
    seeds: str = "",
) -> int:
    command = _append_filters(
        _base_command(),
        tasks=tasks,
        methods=methods,
        perturbations=perturbations,
        latency_conditions=latency_conditions,
        seeds=seeds,
    )
    command.append("--dry-run")
    try:
        return _run_script(command)
    finally:
        volume.commit()


@app.function(
    gpu="A100-40GB",
    volumes={str(VOLUME_ROOT): volume},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=12 * 60 * 60,
)
def run_stage1(
    tasks: str = "",
    methods: str = "",
    perturbations: str = "",
    latency_conditions: str = "",
    seeds: str = "",
) -> int:
    command = _append_filters(
        _base_command(),
        tasks=tasks,
        methods=methods,
        perturbations=perturbations,
        latency_conditions=latency_conditions,
        seeds=seeds,
    )
    command.append("--resume")
    try:
        return _run_script(command)
    finally:
        volume.commit()


@app.local_entrypoint()
def main(
    command: str,
    tasks: str = "",
    methods: str = "",
    perturbations: str = "",
    latency_conditions: str = "",
    seeds: str = "",
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
    if command == "manifest":
        call = write_manifest.spawn()
    elif command == "dry_run":
        call = dry_run.spawn(tasks, methods, perturbations, latency_conditions, seeds)
    elif command == "run":
        call = run_stage1.spawn(tasks, methods, perturbations, latency_conditions, seeds)
    else:
        raise ValueError("unknown command; choose manifest/dry_run/run/status")
    print(f"dispatched {command}; call_id={call.object_id}")
    print(
        "poll with: modal run modal_stage1.py::main --command status "
        f"--call-id {call.object_id}"
    )
