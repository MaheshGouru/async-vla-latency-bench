#!/usr/bin/env python3
"""Select the first task in each suite with >=4/5 ideal-sync successes."""

import argparse
import csv
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if not cfg.checkpoint_revision:
        raise ValueError("checkpoint_revision must be pinned before task selection")

    policy, preprocessor, postprocessor = None, None, None
    output_dir = cfg.output_dir
    ensure_dir(output_dir / "summaries")
    rows = []
    selected = []

    for candidate in cfg.task_candidates:
        chosen_for_candidate = None
        for task_id in candidate.task_ids:
            env = make_libero_env(
                candidate.suite,
                task_id,
                seed=cfg.seeds[0],
                control_mode=cfg.control_mode,
                obs_type=cfg.obs_type,
                camera_name=cfg.camera_name,
                observation_width=cfg.observation_width,
                observation_height=cfg.observation_height,
                init_states=cfg.init_states,
                episode_length=cfg.episode_length,
                num_steps_wait=cfg.num_steps_wait,
            )
            task_info = get_task_info(env, candidate.suite, task_id)

            if policy is None:
                policy = load_pi05_policy(
                    cfg.policy_checkpoint,
                    cfg.checkpoint_revision,
                    n_action_steps=cfg.policy_n_action_steps,
                    device=cfg.device,
                )
                preprocessor, postprocessor = load_pre_post_processors(
                    policy,
                    cfg.policy_checkpoint,
                    cfg.checkpoint_revision,
                )

            successes = 0
            task_rows = []
            for seed in cfg.seeds[:5]:
                env.reset(seed=seed)
                summary = run_episode(
                    env=env,
                    policy=policy,
                    preprocessor=preprocessor,
                    postprocessor=postprocessor,
                    task_instruction=task_info.language_instruction,
                    episode_id=f"{candidate.suite}_tid{task_id}_select_s{seed}",
                    strategy="ideal_sync",
                    latency_profile=LatencyProfile("ideal", False, 0.0),
                    fixed_horizon=10,
                    output_dir=output_dir,
                    seed=seed,
                    device=cfg.device,
                )
                success = bool(summary.get("success", False))
                successes += int(success)
                task_rows.append(
                    {
                        "suite": candidate.suite,
                        "task_id": task_id,
                        "task_name": task_info.task_name,
                        "language_instruction": task_info.language_instruction,
                        "seed": seed,
                        "success": success,
                        "episode_steps": summary.get("environment_steps", 0),
                        "selected": False,
                    }
                )
                if successes >= 4:
                    # continue to record all five seeds for the selected task
                    continue

            is_selected = successes >= 4
            if is_selected and chosen_for_candidate is None:
                chosen_for_candidate = task_id
                for row in task_rows:
                    row["selected"] = True
                selected.append(
                    {
                        "suite": candidate.suite,
                        "task_id": task_id,
                        "task_name": task_info.task_name,
                        "language_instruction": task_info.language_instruction,
                    }
                )

            rows.extend(task_rows)
            if chosen_for_candidate is not None:
                break

    csv_path = output_dir / "summaries" / "task_selection.csv"
    if rows:
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    write_json(output_dir / "summaries" / "selected_tasks.json", selected)

    print(f"selected_tasks={selected}")
    print(f"wrote {csv_path}")
    return 1 if len(selected) < len(cfg.task_candidates) else 0


if __name__ == "__main__":
    raise SystemExit(main())
