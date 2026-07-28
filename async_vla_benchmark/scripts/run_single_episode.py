#!/usr/bin/env python3
"""Run exactly one ideal-sync episode and print/save its summary.

Useful for quickly checking whether a pipeline change (e.g. the observation-
orientation fix in `policy.preprocess_observation`) actually changes task
success, without re-running the full task-selection sweep across every task
and seed.
"""

import argparse
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import write_json
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--suite", default="libero_spatial")
    parser.add_argument("--task-id", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--episode-id", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if not cfg.checkpoint_revision:
        raise ValueError("checkpoint_revision must be pinned before running an episode")

    env = make_libero_env(
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

    policy = load_pi05_policy(
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
        n_action_steps=cfg.policy_n_action_steps,
        device=cfg.device,
    )
    preprocessor, postprocessor = load_pre_post_processors(
        policy, cfg.policy_checkpoint, cfg.checkpoint_revision
    )

    episode_id = args.episode_id or f"{args.suite}_tid{args.task_id}_verify_s{args.seed}"
    env.reset(seed=args.seed)
    summary = run_episode(
        env=env,
        policy=policy,
        preprocessor=preprocessor,
        postprocessor=postprocessor,
        task_instruction=task_info.language_instruction,
        episode_id=episode_id,
        strategy="ideal_sync",
        latency_profile=LatencyProfile("ideal", False, 0.0),
        fixed_horizon=10,
        output_dir=cfg.output_dir,
        seed=args.seed,
        device=cfg.device,
    )
    write_json(cfg.output_dir / "diagnostics" / f"{episode_id}_summary.json", summary)
    print(f"task={task_info.task_name}")
    print(f"success={summary.get('success')}")
    print(f"environment_steps={summary.get('environment_steps')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
