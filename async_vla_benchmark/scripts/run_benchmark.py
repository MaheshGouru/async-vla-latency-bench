#!/usr/bin/env python3
"""Expand the experiment matrix and optionally execute benchmark episodes."""

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from async_vla_benchmark.benchmark.config import BenchmarkConfig, load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors
from async_vla_benchmark.benchmark.queues import request_threshold_for_horizon
from async_vla_benchmark.benchmark.rtc import build_rtc_config, configure_rtc
from async_vla_benchmark.scripts.validate_results import validate_episode


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
    # Spec §15: apply the RTC settings to the policy. PI05Config.rtc_config
    # defaults to None and the pi05_libero_finetuned checkpoint ships null, so
    # without this the policy's _rtc_enabled() is False and LeRobot silently
    # ignores the per-request inference_delay/prev_chunk_left_over/
    # execution_horizon arguments -- no RTC guidance is applied at all.
    # execution_horizon here is only LeRobot's fallback; every request passes
    # its own value derived from the episode's fixed_horizon.
    if cfg.rtc.enabled:
        configure_rtc(
            policy,
            build_rtc_config(
                execution_horizon=cfg.rtc.execution_horizon,
                max_guidance_weight=cfg.rtc.max_guidance_weight,
                prefix_attention_schedule=cfg.rtc.prefix_attention_schedule,
            ),
        )
    preprocessor, postprocessor = load_pre_post_processors(
        policy,
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
    )
    return policy, preprocessor, postprocessor


def _run_experiment(cfg: BenchmarkConfig, tagged_plans: list[tuple[str, EpisodePlan]], args) -> int:
    output_dir = cfg.output_dir
    ensure_dir(output_dir / "requests")
    ensure_dir(output_dir / "actions")
    ensure_dir(output_dir / "episodes")
    ensure_dir(output_dir / "summaries")

    policy = None
    preprocessor = None
    postprocessor = None
    env_cache: dict[str, Any] = {}
    summaries_by_experiment: dict[str, list] = {}
    core_summaries_by_episode_id: dict[str, dict] = {}

    for experiment_name, plan in tagged_plans:
        episode_id = _episode_id(plan)
        episode_json = output_dir / "episodes" / f"{episode_id}.json"

        # horizon_sweep's h=10 rows are, for shared (task, seed, strategy,
        # profile), literally the same episode the core experiment already
        # ran (spec §16: "may reuse validated runs from the core
        # experiment"). Re-running them wastes compute and, worse, silently
        # overwrites core's raw episode/request/action files (both write to
        # the same episode_id-keyed paths). Reuse core's result instead of
        # re-executing: check this run's own core results first, then fall
        # back to an already-written episode file from a prior run.
        if experiment_name == "horizon_sweep" and plan.fixed_horizon == 10:
            reused = core_summaries_by_episode_id.get(episode_id)
            if reused is None and episode_json.exists():
                reused = json.loads(episode_json.read_text())
            if reused is not None:
                summaries_by_experiment.setdefault(experiment_name, []).append(reused)
                print(f"reused {episode_id} from core: success={reused['success']} [{experiment_name}]")
                continue

        if args.resume and episode_json.exists() and not args.overwrite:
            # Spec §22: "--resume must skip only completed *and validated* episodes."
            # Existence alone is not completion -- an episode that crashed after
            # writing its summary but before flushing a full parquet would otherwise
            # be skipped permanently, and a resumed long run would silently carry the
            # gap forward.
            existing = json.loads(episode_json.read_text())
            errors = validate_episode(output_dir, episode_id, existing)
            if not errors:
                print(f"skip {episode_id}: already completed and validated")
                continue
            print(f"rerun {episode_id}: prior run failed validation ({len(errors)} errors)")

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

        # RTC is configured once, on the policy object that also serves
        # ideal_sync/blocking_sync/naive_async. Scope the flag to the episodes that
        # actually ask for it so a non-RTC arm can never reach a guided code path.
        # This is a guard rather than a diagnosis: whether LeRobot's plain
        # `predict_action_chunk(batch)` consults `_rtc_enabled()` when passed no RTC
        # arguments is unverified, and a contaminated control arm would be invisible
        # in the outputs -- the RTC diagnostics are only recorded for RTC episodes,
        # so a spoiled naive_async run looks entirely normal.
        if cfg.rtc.enabled:
            policy.config.rtc_config.enabled = plan.strategy == "rtc"

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
            # Spec §16: the horizon sweep sets rtc.execution_horizon = fixed_horizon
            # and request_threshold_actions = ceil(fixed_horizon / 2), using the same
            # values for paired naive_async and RTC runs. Both are derived from the
            # plan's horizon rather than read from cfg.rtc, which carries a single
            # constant and would otherwise apply h=10's settings to every sweep cell.
            rtc_execution_horizon=plan.fixed_horizon,
            request_threshold_actions=request_threshold_for_horizon(plan.fixed_horizon),
            device=cfg.device,
        )
        summaries_by_experiment.setdefault(experiment_name, []).append(summary)
        if experiment_name == "core":
            core_summaries_by_episode_id[episode_id] = summary
        print(
            f"completed {episode_id}: success={summary['success']} "
            f"steps={summary['environment_steps']} [{experiment_name}]"
        )

    # Write aggregate summaries, one file per experiment represented in this run.
    #
    # Merge into whatever the file already holds rather than replacing it. A
    # filtered run (--strategy/--latency-profile/--task/--seed) only produces the
    # subset it was asked for, so a plain overwrite would silently drop every
    # episode outside the filter -- e.g. `--strategy naive_async` would leave
    # core_summaries.json containing only naive_async rows, and make_figures.py
    # would then build figures from a fraction of the data. Episodes are keyed by
    # episode_id, so a rerun of the same condition replaces its own stale row.
    for experiment_name, summaries in summaries_by_experiment.items():
        path = output_dir / "summaries" / f"{experiment_name}_summaries.json"
        merged: dict[str, dict] = {}
        if path.exists():
            for existing in json.loads(path.read_text()):
                merged[existing["episode_id"]] = existing
        for summary in summaries:
            merged[summary["episode_id"]] = summary
        write_json(path, [merged[key] for key in sorted(merged)])
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--experiment", choices=("core", "horizon_sweep", "all"), required=True)
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
    if args.output_dir:
        cfg.output_dir = args.output_dir
        cfg.selected_tasks_file = str(cfg.output_dir / "summaries" / "selected_tasks.json")
    default_tasks = _selected_tasks_from_file(Path(cfg.selected_tasks_file))
    tasks = args.task if args.task else default_tasks
    if not tasks:
        raise ValueError(
            "no tasks selected; run select_tasks.py first or pass one or more --task suite:id"
        )
    core_seeds = args.seed or [0, 1, 2, 3, 4]
    horizon_seeds = args.seed or [0, 1, 2]
    if args.experiment == "core":
        tagged_plans = [("core", p) for p in core_plans(tasks, core_seeds)]
    elif args.experiment == "horizon_sweep":
        tagged_plans = [("horizon_sweep", p) for p in horizon_plans(tasks, horizon_seeds)]
    else:
        # Run both plan sets in one policy-load session (one container), so every
        # episode across both experiments shares identical hardware/runtime conditions.
        tagged_plans = [("core", p) for p in core_plans(tasks, core_seeds)] + [
            ("horizon_sweep", p) for p in horizon_plans(tasks, horizon_seeds)
        ]
    filters = {
        "strategy": args.strategy,
        "latency_profile": args.latency_profile,
        "fixed_horizon": args.fixed_horizon,
    }
    selected = [
        (name, p)
        for name, p in tagged_plans
        if all(value is None or getattr(p, key) == value for key, value in filters.items())
    ]
    if args.dry_run:
        for index, (name, plan) in enumerate(selected, 1):
            print(index, name, asdict(plan))
        print(f"planned_episodes={len(selected)}")
        return 0
    return _run_experiment(cfg, selected, args)


if __name__ == "__main__":
    raise SystemExit(main())
