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


def resolve_checkpoint_revision_sha(checkpoint: str, revision: str | None) -> str | None:
    """Resolve `checkpoint`@`revision` to the exact commit SHA that
    `PI05Config.from_pretrained`/`PI05Policy.from_pretrained` would load — the
    same check the Days 4-8 audit needs to confirm the pinned checkpoint
    hasn't drifted (see docs/DAYS_4_8_SPEC.md ("exact checkpoint loaded on
    CUDA")).
    """
    if not revision:
        return None
    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError

    try:
        return HfApi().model_info(checkpoint, revision=revision).sha
    except HfHubHTTPError:
        return None


def pip_vcs_commit(name):
    """Read the pinned VCS commit pip recorded for a `pip install git+URL@commit`
    install, via the PEP 610 `direct_url.json` dist-info file. A `git rev-parse`
    checkout scan (see `git_commit`) can't find this: pip builds a wheel from the
    git source and discards the `.git` directory, so no checkout is importable
    even though the exact commit *is* known and pinned.
    """
    try:
        dist = importlib.metadata.distribution(name)
        text = dist.read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        return None
    if not text:
        return None
    try:
        direct_url = json.loads(text)
    except json.JSONDecodeError:
        return None
    return direct_url.get("vcs_info", {}).get("commit_id")


def main(output_dir: Path | None = None, config_path: Path | None = None):
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
    commit = pip_vcs_commit("lerobot")
    if commit is None:
        spec = importlib.util.find_spec("lerobot")
        if spec and spec.origin:
            commit = git_commit(Path(spec.origin).resolve().parents[2])
    metadata["lerobot_git_commit"] = commit

    from async_vla_benchmark.benchmark.config import load_config

    cfg = load_config(config_path or ROOT / "configs" / "days1_3.yaml")
    metadata["checkpoint_revision_sha"] = resolve_checkpoint_revision_sha(
        cfg.policy_checkpoint, cfg.checkpoint_revision
    )
    if cfg.checkpoint_revision and metadata["checkpoint_revision_sha"] is None:
        metadata["deviations"].append(
            f"Could not resolve checkpoint_revision {cfg.checkpoint_revision!r} for "
            f"{cfg.policy_checkpoint!r} against the Hub."
        )
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
    metadata["status"] = "ready" if not metadata["deviations"] else "not_ready"
    output = (output_dir or ROOT / "outputs") / "environment.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 1 if metadata["deviations"] else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.output_dir, args.config))
