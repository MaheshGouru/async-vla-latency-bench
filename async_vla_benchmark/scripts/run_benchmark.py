#!/usr/bin/env python3
"""Expand the experiment matrix; real execution remains adapter-gated."""

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path


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
    tasks = args.task or ["libero_spatial:selected", "libero_goal:selected", "libero_10:selected"]
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
    raise RuntimeError(
        "real execution requires the pinned LeRobot/LIBERO CUDA environment and selected-task manifest; "
        "use --dry-run on this host"
    )


if __name__ == "__main__":
    raise SystemExit(main())
