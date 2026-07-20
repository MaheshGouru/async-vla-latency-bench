#!/usr/bin/env python3
"""Expand the experiment matrix and optionally execute benchmark episodes."""

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from async_vla_benchmark.benchmark.config import BenchmarkConfig, load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors


@dataclass(frozen=True)
class EpisodePlan:
    task: str
    seed: int
    strategy: str
    latency_profile: str
    fixed_horizon: int


def core_plans(tasks, seeds):
    for task in tasks:
        for seed in seeds:
            yield EpisodePlan(task, seed, "ideal_sync", "ideal", 10)
            for strategy in ("blocking_sync", "naive_async", "rtc"):
                for profile in ("native", "native_plus_300", "native_plus_700"):
                    yield EpisodePlan(task, seed, strategy, profile, 10)


def horizon_plans(tasks, seeds=(0, 1, 2)):
    for task in tasks:
        for seed in seeds:
            for strategy in ("naive_async", "rtc"):
                for profile in ("native", "native_plus_700"):
                    for horizon in (2, 5, 10):
                        yield EpisodePlan(task, seed, strategy, profile, horizon)


def _selected_tasks_from_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [f"{item['suite']}:{item['task_id']}" for item in data]


def _parse_task(task: str) -> tuple[str, int]:
    suite, task_id = task.split(":")
    return suite, int(task_id)


def _episode_id(plan: EpisodePlan) -> str:
    suite, task_id = _parse_task(plan.task)
    return (
        f"{suite}_tid{task_id}_"
        f"{plan.strategy}_{plan.latency_profile}_h{plan.fixed_horizon}_s{plan.seed}"
    )


def _load_policy_and_processors(cfg: BenchmarkConfig):
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
    return policy, preprocessor, postprocessor


def _run_experiment(cfg: BenchmarkConfig, plans: list[EpisodePlan], args) -> int:
    output_dir = cfg.output_dir
    ensure_dir(output_dir / "requests")
    ensure_dir(output_dir / "actions")
    ensure_dir(output_dir / "episodes")
    ensure_dir(output_dir / "summaries")

    policy = None
    preprocessor = None
    postprocessor = None
    env_cache: dict[str, Any] = {}
    summaries = []

    for plan in plans:
        episode_id = _episode_id(plan)
        episode_json = output_dir / "episodes" / f"{episode_id}.json"
        if args.resume and episode_json.exists() and not args.overwrite:
            print(f"skip {episode_id}: already completed")
            continue

        suite, task_id = _parse_task(plan.task)
        env_key = f"{suite}:{task_id}"
        if env_key not in env_cache:
            env_cache[env_key] = make_libero_env(
                suite,
                task_id,
                seed=plan.seed,
                control_mode=cfg.control_mode,
                obs_type=cfg.obs_type,
                camera_name=cfg.camera_name,
                observation_width=cfg.observation_width,
                observation_height=cfg.observation_height,
                init_states=cfg.init_states,
                episode_length=cfg.episode_length,
                num_steps_wait=cfg.num_steps_wait,
            )
        env = env_cache[env_key]

        if policy is None:
            policy, preprocessor, postprocessor = _load_policy_and_processors(cfg)

        latency_profile = next(
            (p for p in cfg.latency_profiles if p.name == plan.latency_profile), None
        )
        if latency_profile is None:
            raise ValueError(f"unknown latency profile {plan.latency_profile}")
        profile = LatencyProfile(
            latency_profile.name,
            latency_profile.use_measured_native_latency,
            latency_profile.added_latency_ms,
        )

        task_info = get_task_info(env, suite, task_id)
        summary = run_episode(
            env=env,
            policy=policy,
            preprocessor=preprocessor,
            postprocessor=postprocessor,
            task_instruction=task_info.language_instruction,
            episode_id=episode_id,
            strategy=plan.strategy,
            latency_profile=profile,
            fixed_horizon=plan.fixed_horizon,
            output_dir=output_dir,
            seed=plan.seed,
            use_rtc=(plan.strategy == "rtc"),
            rtc_execution_horizon=cfg.rtc.execution_horizon,
            device=cfg.device,
        )
        summaries.append(summary)
        print(f"completed {episode_id}: success={summary['success']} steps={summary['environment_steps']}")

    # Write aggregate summaries
    if summaries:
        write_json(output_dir / "summaries" / f"{args.experiment}_summaries.json", summaries)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--experiment", choices=("core", "horizon_sweep"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--task", action="append")
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--strategy")
    parser.add_argument("--latency-profile")
    parser.add_argument("--fixed-horizon", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.resume and args.overwrite:
        parser.error("--resume and --overwrite are mutually exclusive")

    cfg = load_config(args.config)
    default_tasks = _selected_tasks_from_file(Path(cfg.selected_tasks_file))
    tasks = args.task if args.task else default_tasks
    if not tasks:
        raise ValueError(
            "no tasks selected; run select_tasks.py first or pass one or more --task suite:id"
        )
    seeds = args.seed or ([0, 1, 2, 3, 4] if args.experiment == "core" else [0, 1, 2])
    plans = core_plans(tasks, seeds) if args.experiment == "core" else horizon_plans(tasks, seeds)
    filters = {
        "strategy": args.strategy,
        "latency_profile": args.latency_profile,
        "fixed_horizon": args.fixed_horizon,
    }
    selected = [p for p in plans if all(value is None or getattr(p, key) == value for key, value in filters.items())]
    if args.dry_run:
        for index, plan in enumerate(selected, 1):
            print(index, asdict(plan))
        print(f"planned_episodes={len(selected)}")
        return 0
    return _run_experiment(cfg, selected, args)


if __name__ == "__main__":
    raise SystemExit(main())
