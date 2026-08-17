#!/usr/bin/env python3
"""Execute one Stage 3C scene shard (reset/fingerprint only; no policy)."""
import argparse
import hashlib
import importlib.metadata
import os
import subprocess
from pathlib import Path
import yaml

from async_vla_benchmark.benchmark.environment import (
    available_initialization_count, get_task_info, initial_state_fingerprint, make_libero_env,
    make_libero_plus_env, resolve_episode_index,
)
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage3c import (
    ENV_CONSTRUCTION_SEED, FINGERPRINT_METHOD, FINGERPRINT_SCHEMA,
    INITIALIZATION_INDICES, REPEAT_IDS, TASKS, assert_frozen_variants,
)
from async_vla_benchmark.scripts.run_stage1 import _configure_libero_home


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha(path):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--frozen-variants", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scene", choices=("id", "ood"), required=True)
    parser.add_argument("--libero-plus-repo", type=Path, required=True)
    args = parser.parse_args()
    if args.scene == "ood":
        native = Path.home() / "stage1-native"
        if native.exists() and os.environ.get("STAGE3C_NATIVE_REEXEC") != str(native):
            environment = os.environ.copy()
            environment.update({
                "STAGE3C_NATIVE_REEXEC": str(native), "MAGICK_HOME": str(native),
                "PATH": str(native / "bin") + os.pathsep + environment.get("PATH", ""),
                "LD_LIBRARY_PATH": str(native / "lib") + os.pathsep + environment.get("LD_LIBRARY_PATH", ""),
            })
            os.execve(os.sys.executable, [os.sys.executable, *os.sys.argv], environment)
        from wand.api import library as _wand_library  # noqa: F401

    cfg = yaml.safe_load(args.config.read_text())
    if not isinstance(cfg, dict):
        raise ValueError("Stage 3C environment config must be a mapping")
    frozen = read_csv(args.frozen_variants)
    assert_frozen_variants(frozen)
    _configure_libero_home(args.scene)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "stage3c_initialization_audit.csv"
    previous = read_csv(output) if output.exists() else []
    rows = [row for row in previous if row.get("scene_condition") != args.scene]
    benchmark_repo_sha = git_sha(Path.cwd())
    libero_plus_sha = git_sha(args.libero_plus_repo)
    try:
        libero_package_version = importlib.metadata.version("hf_libero")
    except importlib.metadata.PackageNotFoundError:
        libero_package_version = "unavailable"
    spec_hash = sha256(args.spec)
    maker = make_libero_plus_env if args.scene == "ood" else make_libero_env

    for task_key, task in TASKS.items():
        task_index = task["api_task_index"] if args.scene == "ood" else task["base_task_id"]
        expected_name = task["variant_name"] if args.scene == "ood" else task["base_task_name"]
        for initialization_index in INITIALIZATION_INDICES:
            for repeat_id in REPEAT_IDS:
                env = maker(
                    task["suite"], task_index, seed=ENV_CONSTRUCTION_SEED,
                    control_mode=cfg["control_mode"], obs_type=cfg["obs_type"],
                    camera_name=cfg["camera_name"], observation_width=cfg["observation_width"],
                    observation_height=cfg["observation_height"], init_states=cfg["init_states"],
                    episode_length=cfg["episode_length"], num_steps_wait=cfg["num_steps_wait"],
                    episode_index=initialization_index,
                )
                try:
                    actual_name = get_task_info(env, task["suite"], task_index).task_name
                    if actual_name != expected_name:
                        raise RuntimeError(f"task mismatch: {actual_name!r} != {expected_name!r}")
                    resolved = resolve_episode_index(env)
                    initialization_state_count = available_initialization_count(env)
                    method, fingerprint = initial_state_fingerprint(env, None)
                    if method != FINGERPRINT_METHOD:
                        raise RuntimeError(f"unsupported Stage 3C fingerprint method: {method}")
                finally:
                    if hasattr(env, "close"):
                        env.close()
                rows.append({
                    "stage": "stage3c", "task_key": task_key,
                    "suite": task["suite"], "base_task_id": task["base_task_id"],
                    "base_task_name": task["base_task_name"],
                    "scene_condition": args.scene,
                    "variant_name_or_id": expected_name,
                    "perturbation_key": "object_layout" if args.scene == "ood" else "id",
                    "classification_id": task["classification_id"] if args.scene == "ood" else "",
                    "api_task_index": task_index,
                    "difficulty_level": task["difficulty_level"] if args.scene == "ood" else "",
                    "requested_initialization_index": initialization_index,
                    "resolved_initialization_index_or_id": resolved,
                    "available_initialization_state_count": initialization_state_count,
                    "repeat_id": repeat_id,
                    "initial_state_fingerprint": fingerprint,
                    "fingerprint_schema_version": method,
                    "fingerprint_canonical_schema": FINGERPRINT_SCHEMA,
                    # The pinned vanilla environment is a PyPI package rather
                    # than a Git checkout; keep the SHA field explicitly empty
                    # instead of mislabeling a package version as a commit.
                    "libero_git_sha": "",
                    "libero_package_version": libero_package_version,
                    "libero_plus_git_sha": libero_plus_sha,
                    "benchmark_repo_sha": benchmark_repo_sha,
                    "env_construction_seed": ENV_CONSTRUCTION_SEED,
                    "stage3c_spec_hash": spec_hash,
                    "policy_rollout_seed": "",
                    "policy_inference_executed": False,
                    "action_steps_executed": 0,
                })
                print(args.scene, task_key, f"requested={initialization_index}",
                      f"resolved={resolved}", f"available={initialization_state_count}",
                      f"repeat={repeat_id}", fingerprint)
    write_csv(output, rows)
    print(f"PASS: Stage 3C {args.scene} shard wrote {len(TASKS)*len(INITIALIZATION_INDICES)*len(REPEAT_IDS)} reset-only rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
