#!/usr/bin/env python3
"""Resolve Stage 3 reset fingerprints one scene environment at a time."""
import argparse
import os
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import (
    get_task_info, initial_state_fingerprint, make_libero_env,
    make_libero_plus_env, resolve_episode_index, seed_environment_rng,
)
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.scripts.run_stage1 import _configure_libero_home


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--scene", choices=("id", "ood"), required=True)
    parser.add_argument("--expected-rows", type=int, default=288)
    parser.add_argument("--expected-cells-per-key", type=int, default=6)
    parser.add_argument("--audit-output", type=Path)
    args = parser.parse_args()
    if args.scene == "ood":
        native = Path.home() / "stage1-native"
        if native.exists() and os.environ.get("STAGE3_NATIVE_REEXEC") != str(native):
            environment = os.environ.copy(); environment["STAGE3_NATIVE_REEXEC"] = str(native)
            environment["MAGICK_HOME"] = str(native)
            environment["PATH"] = str(native / "bin") + os.pathsep + environment.get("PATH", "")
            environment["LD_LIBRARY_PATH"] = str(native / "lib") + os.pathsep + environment.get("LD_LIBRARY_PATH", "")
            os.execve(os.sys.executable, [os.sys.executable, *os.sys.argv], environment)
        # Load Conda's MagickWand before LIBERO/PyTorch so its transitive C++
        # runtime wins the loader-order race in the no-sudo Jupyter image.
        from wand.api import library as _wand_library  # noqa: F401
    cfg = load_config(args.config); rows = read_csv(args.manifest)
    if len(rows) != args.expected_rows: raise ValueError(f"expected {args.expected_rows} Stage 3 rows, got {len(rows)}")
    _configure_libero_home(args.scene)
    selected = [r for r in rows if r["scene"] == args.scene]
    identities = {}; audit_rows = []
    keys = sorted({(r["task_key"], r["variant_name"], int(r["api_task_index"]), int(r["seed"])) for r in selected})
    for task_key, variant_name, task_index, seed in keys:
        row = next(r for r in selected if r["task_key"] == task_key and r["variant_name"] == variant_name and int(r["seed"]) == seed)
        maker = make_libero_plus_env if args.scene == "ood" else make_libero_env

        def resolve_fresh_environment():
            # Match the production lifecycle exactly: construct a fresh wrapper
            # (whose constructor performs its own reset), then perform the single
            # seeded reset used by EpisodeRunner.run and fingerprint immediately.
            seed_environment_rng(seed)
            requested_index = int(row.get("requested_initialization_index", "0"))
            is_experiment_a = row.get("stage", row.get("stage_or_experiment_label", "")) == "experiment_a"
            env = maker(row["suite"], task_index, seed=seed, control_mode=cfg.control_mode,
                obs_type=cfg.obs_type, camera_name=cfg.camera_name, observation_width=cfg.observation_width,
                observation_height=cfg.observation_height, init_states=cfg.init_states,
                episode_length=cfg.episode_length, num_steps_wait=cfg.num_steps_wait,
                episode_index=requested_index, reset_on_create=not is_experiment_a)
            try:
                actual = get_task_info(env, row["suite"], task_index).task_name
                if actual != variant_name: raise RuntimeError(f"task mismatch: {actual!r} != {variant_name!r}")
                resolved_index = resolve_episode_index(env)
                if resolved_index != requested_index:
                    raise RuntimeError(f"requested episode_index={requested_index} resolved as {resolved_index}")
                import torch
                seed_environment_rng(seed); torch.manual_seed(seed)
                observation, _ = env.reset(seed=seed)
                return (*initial_state_fingerprint(env, observation), resolved_index)
            finally:
                if hasattr(env, "close"): env.close()

        method, fingerprint, resolved_index = resolve_fresh_environment()
        repeated_method, repeated_fingerprint, repeated_resolved = resolve_fresh_environment()
        if (method, fingerprint, resolved_index) != (repeated_method, repeated_fingerprint, repeated_resolved):
            raise RuntimeError(f"non-repeatable fresh-environment fingerprint for {task_key}/{variant_name}/seed={seed}")
        identities[(task_key, variant_name, seed, args.scene)] = ("libero_episode_index:0", method, fingerprint)
        audit_rows.append({"scene":args.scene,"task_key":task_key,"variant_name":variant_name,
            "api_task_index":task_index,"seed":seed,"initialization_index_or_id":"libero_episode_index:0",
            "requested_initialization_index":0,"resolved_initialization_index_or_id":resolved_index,
            "fingerprint_method":method,"fingerprint":fingerprint,"repeat_fingerprint":repeated_fingerprint,
            "repeatability_pass":True,"canonical_schema":"qpos,qvel,act,ctrl,mocap_pos,mocap_quat; float64 little-endian; round=1e-12; excludes sim time"})
        print(args.scene, task_key, seed, method, fingerprint)
    for row in selected:
        identity, method, fingerprint = identities[(row["task_key"], row["variant_name"], int(row["seed"]), args.scene)]
        row["initialization_index_or_id"] = identity
        row["initial_state_fingerprint_method"] = method
        row["initial_state_fingerprint"] = fingerprint
        row["requested_initialization_index"] = "0"
        row["resolved_initialization_index_or_id"] = "0"
    groups, counts = defaultdict(set), defaultdict(int)
    for row in selected:
        key = (row["task_key"], row["variant_name"], row["seed"], row["scene"])
        groups[key].add((row["initialization_index_or_id"], row["initial_state_fingerprint_method"], row["initial_state_fingerprint"]))
        counts[key] += 1
    if set(counts.values()) != {args.expected_cells_per_key} or any(len(v) != 1 for v in groups.values()):
        raise ValueError(f"Stage 3 {args.scene} pairing invariant failed")
    write_csv(args.manifest, rows)
    if args.audit_output:
        previous = read_csv(args.audit_output) if args.audit_output.exists() else []
        retained = [r for r in previous if r.get("scene") != args.scene]
        write_csv(args.audit_output, retained + audit_rows)
    print(f"PASS: resolved {len(identities)} {args.scene} identities; {args.expected_cells_per_key} treatment cells paired per key")
    return 0


if __name__ == "__main__": raise SystemExit(main())
