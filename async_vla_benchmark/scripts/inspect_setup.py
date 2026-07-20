#!/usr/bin/env python3
"""Inspect the execution stack and write facts without claiming readiness."""

import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def package(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def git_commit(path):
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    packages = {name: package(name) for name in ("lerobot", "torch", "mujoco", "robosuite", "libero")}
    metadata = {
        "status": "not_ready",
        "platform": platform.platform(),
        "python_version": sys.version,
        "lerobot_git_commit": None,
        "checkpoint_revision_sha": None,
        "dataset_revision_sha": None,
        "packages": packages,
        "cuda_version": None,
        "cuda_available": False,
        "nvidia_driver": None,
        "gpu_model": None,
        "deviations": [],
    }
    spec = importlib.util.find_spec("lerobot")
    if spec and spec.origin:
        metadata["lerobot_git_commit"] = git_commit(Path(spec.origin).resolve().parents[2])
    try:
        import torch
        metadata["cuda_version"] = torch.version.cuda
        metadata["cuda_available"] = torch.cuda.is_available()
        if metadata["cuda_available"]:
            metadata["gpu_model"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    if not metadata["lerobot_git_commit"]:
        metadata["deviations"].append("No pinned LeRobot Git checkout is importable.")
    if not metadata["cuda_available"]:
        metadata["deviations"].append("CUDA is unavailable; experiments cannot run here.")
    output = ROOT / "outputs" / "environment.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 1 if metadata["deviations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
