#!/usr/bin/env python3
"""Freeze and validate the 15 unique Stage 2 task×seed reset identities."""

import argparse
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import (
    get_task_info, initial_state_fingerprint, make_libero_env,
)
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.scripts.run_stage1 import _configure_libero_home


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)
    rows = read_csv(args.manifest)
    if len(rows) != 360:
        raise ValueError(f"expected 360 Stage 2 rows, got {len(rows)}")
    _configure_libero_home("id")
    identities = {}
    for task_key, suite, task_id, seed in sorted({
        (row["task_key"], row["suite"], int(row["task_id"]), int(row["seed"]))
        for row in rows
    }):
        env = make_libero_env(
            suite, task_id, seed=seed,
            control_mode=cfg.control_mode, obs_type=cfg.obs_type,
            camera_name=cfg.camera_name, observation_width=cfg.observation_width,
            observation_height=cfg.observation_height, init_states=cfg.init_states,
            episode_length=cfg.episode_length, num_steps_wait=cfg.num_steps_wait,
        )
        try:
            expected_name = next(
                row["task_name"] for row in rows
                if row["task_key"] == task_key and int(row["seed"]) == seed
            )
            actual_name = get_task_info(env, suite, task_id).task_name
            if actual_name != expected_name:
                raise RuntimeError(f"task mismatch: {actual_name!r} != {expected_name!r}")
            # Match ExecutionEngine.run's RNG ordering exactly before the reset
            # whose state is frozen into the manifest.
            import torch
            torch.manual_seed(seed)
            observation, _ = env.reset(seed=seed)
            method, fingerprint = initial_state_fingerprint(env, observation)
        finally:
            if hasattr(env, "close"):
                env.close()
        identities[(task_key, seed)] = (
            "libero_episode_index:0", method, fingerprint
        )
        print(task_key, seed, method, fingerprint)
    if len(identities) != 15:
        raise ValueError(f"expected 15 task×seed identities, got {len(identities)}")
    for row in rows:
        identity, method, fingerprint = identities[(row["task_key"], int(row["seed"]))]
        row["initialization_index_or_id"] = identity
        row["initial_state_fingerprint_method"] = method
        row["initial_state_fingerprint"] = fingerprint
    groups = defaultdict(set)
    counts = defaultdict(int)
    for row in rows:
        key = (row["task_key"], row["seed"])
        groups[key].add((
            row["initialization_index_or_id"], row["initial_state_fingerprint_method"],
            row["initial_state_fingerprint"],
        ))
        counts[key] += 1
    if set(counts.values()) != {24} or any(len(value) != 1 for value in groups.values()):
        raise ValueError("Stage 2 pairing invariant failed before dispatch")
    write_csv(args.manifest, rows)
    print("PASS: resolved 15 reset identities; all 24 cells per task×seed are paired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
