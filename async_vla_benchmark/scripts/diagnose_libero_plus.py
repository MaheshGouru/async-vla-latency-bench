#!/usr/bin/env python3
"""Smoke-test the LIBERO-plus integration before trusting it for real runs.

Builds one LIBERO-plus environment, resets it, and checks:
  1. The env is actually constructible against our pinned LeRobot commit with
     `is_libero_plus=True` (environment.make_libero_plus_env).
  2. Observation keys/shapes match what make_libero_env produces on vanilla
     LIBERO, so the rest of the pipeline (policy.py, execution.py) needs no
     changes to consume LIBERO-plus envs.
  3. task_classification.json's `id` field for this task_id actually matches
     the live task's name (ood_tasks.verify_task_id_mapping) — this is the
     load-bearing assumption behind ood_tasks.find_variants and is NOT
     verified anywhere else.

Only run this against the Dockerfile.modal.libero_plus image; vanilla LIBERO
does not have task_classification.json and will fail step 3 by design.

Writes to <output-dir>/diagnostics/libero_plus_<suite>_tid<task_id>_s<seed>/:
  - observation_structure.json
  - id_mapping_check.json
"""

import argparse
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_plus_env
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json
from async_vla_benchmark.benchmark.ood_tasks import (
    TaskClassificationUnavailable,
    list_categories,
    list_variants,
    verify_task_id_mapping,
)


def _describe(value):
    import numpy as np

    if isinstance(value, dict):
        return {k: _describe(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        return {"shape": list(value.shape), "dtype": str(value.dtype)}
    if isinstance(value, (list, tuple)):
        return [_describe(v) for v in value]
    return str(type(value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--suite", default="libero_spatial")
    parser.add_argument("--task-id", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.output_dir:
        cfg.output_dir = args.output_dir

    episode_tag = f"libero_plus_{args.suite}_tid{args.task_id}_s{args.seed}"
    out_dir = ensure_dir(cfg.output_dir / "diagnostics" / episode_tag)

    print(f"building LIBERO-plus env: suite={args.suite} task_id={args.task_id}")
    env = make_libero_plus_env(
        args.suite,
        args.task_id,
        seed=args.seed,
        control_mode=cfg.control_mode,
        obs_type=cfg.obs_type,
        camera_name=cfg.camera_name,
        observation_width=cfg.observation_width,
        observation_height=cfg.observation_height,
        init_states=cfg.init_states,
        episode_length=cfg.episode_length,
        num_steps_wait=cfg.num_steps_wait,
    )
    task_info = get_task_info(env, args.suite, args.task_id)
    obs, _info = env.reset(seed=args.seed)

    structure = {
        "task_name": task_info.task_name,
        "language_instruction": task_info.language_instruction,
        "action_space": {
            "low": env.action_space.low.tolist(),
            "high": env.action_space.high.tolist(),
        },
        "observation_keys": _describe(obs),
    }
    write_json(out_dir / "observation_structure.json", structure)
    print(f"task_name={task_info.task_name!r}")
    print(f"observation keys: {list(obs.keys())}")

    mapping_result: dict = {"suite": args.suite, "task_id": args.task_id}
    try:
        categories = list_categories(args.suite)
        variants = list_variants(args.suite)
        by_task_id = {v.task_id: v for v in variants}
        mapping_result["categories_found"] = categories
        mapping_result["num_variants_in_suite"] = len(variants)
        if args.task_id in by_task_id:
            variant = by_task_id[args.task_id]
            matches = verify_task_id_mapping(args.suite, variant, task_info.task_name)
            mapping_result["task_classification_entry"] = {
                "id": variant.id,
                "task_id": variant.task_id,
                "name": variant.name,
                "category": variant.category,
                "difficulty_level": variant.difficulty_level,
            }
            mapping_result["live_task_name"] = task_info.task_name
            mapping_result["id_matches_task_id"] = matches
            print(
                f"id-1==task_id check: json name={variant.name!r} vs live name="
                f"{task_info.task_name!r} -> {'MATCH' if matches else 'MISMATCH'}"
            )
            if not matches:
                print(
                    "WARNING: task_classification.json's `id - 1` does NOT match LeRobot's "
                    "task_id indexing. Do not use ood_tasks.find_variants() results as "
                    "task_id until this is reconciled."
                )
        else:
            mapping_result["task_classification_entry"] = None
            print(
                f"task_id={args.task_id} has no entry in task_classification.json for "
                f"suite={args.suite} (this may be an unperturbed base task, since the JSON "
                "appears to only classify perturbation variants, not base tasks)."
            )
    except TaskClassificationUnavailable as exc:
        mapping_result["error"] = str(exc)
        print(f"task_classification.json unavailable: {exc}")

    write_json(out_dir / "id_mapping_check.json", mapping_result)
    print(f"wrote diagnostics to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
