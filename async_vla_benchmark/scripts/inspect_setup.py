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
    """Resolve an installed package's version.

    Tries the distribution name first, then case variants, then the imported
    module's `__version__`. LIBERO in particular installs from git under a
    distribution name that does not always match the import name, which is why
    a plain `importlib.metadata.version` lookup recorded `null` for it.
    """
    for candidate in (name, name.upper(), name.capitalize()):
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
    try:
        module = importlib.import_module(name)
    except Exception:
        return None
    version = getattr(module, "__version__", None)
    return str(version) if version is not None else None


def nvidia_driver_version():
    """Read the driver version from `nvidia-smi` (spec §2 requires it recorded)."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip().splitlines()[0].strip() or None


def installed_packages():
    """Full installed-package inventory (spec §2: "installed Python packages")."""
    found = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"]
        if name:
            found[name] = dist.version
    return dict(sorted(found.items(), key=lambda item: item[0].lower()))


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


def resolve_dataset_revision_sha(dataset: str, revision: str | None) -> str | None:
    """Resolve the dataset repo to an exact commit SHA (spec §2: "dataset
    revision SHA").

    Unlike the checkpoint, the dataset is intentionally unpinned in the config
    (it trains nothing here — it only defines LIBERO preprocessing and
    normalization conventions). Resolve `main` in that case so the SHA actually
    in use is still recorded rather than left null.
    """
    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError

    try:
        return HfApi().dataset_info(dataset, revision=revision or "main").sha
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
        "installed_packages": installed_packages(),
        "cuda_version": None,
        "cuda_available": False,
        "nvidia_driver": nvidia_driver_version(),
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
    # An unpinned checkpoint is the risk class that caused the LEROBOT_COMMIT
    # latency drift; record it as a deviation rather than silently writing null.
    if not cfg.checkpoint_revision:
        metadata["deviations"].append(
            f"checkpoint_revision is unpinned for {cfg.policy_checkpoint!r}; "
            "results cannot be attributed to an exact checkpoint."
        )
    metadata["dataset_revision_sha"] = resolve_dataset_revision_sha(
        cfg.dataset_repo, cfg.dataset_revision
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
