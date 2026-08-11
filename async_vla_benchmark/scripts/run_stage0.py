#!/usr/bin/env python3
"""Generate and execute the frozen 96-episode Stage 0 calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from async_vla_benchmark.benchmark.config import BenchmarkConfig, load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import ensure_dir, write_csv, write_json
from async_vla_benchmark.benchmark.queues import request_threshold_for_horizon
from async_vla_benchmark.benchmark.stage0 import (
    REFINEMENT_DELAYS_MS,
    REFINEMENT_STAGE,
    Stage0Plan,
    manifest_rows,
    manifest_rows_for_plans,
    plan_asdict,
    stage0_plans,
    stage0_refinement_plans,
    summary_metadata,
    validate_stage0_config,
)
from async_vla_benchmark.scripts.run_benchmark import _load_policy_and_processors
from async_vla_benchmark.scripts.validate_results import validate_episode


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "stage0_latency_calibration.yaml"


def _gpu_id() -> str | None:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(torch.cuda.current_device())
    except Exception:
        return None
    return None


def _assert_task(plan: Stage0Plan, live_task_name: str) -> None:
    if live_task_name != plan.task.task_name:
        raise RuntimeError(
            f"Stage 0 task mismatch for {plan.task_ref}: expected "
            f"{plan.task.task_name!r}, got {live_task_name!r}"
        )


def _identity_errors(cfg: BenchmarkConfig, plan: Stage0Plan, summary: dict[str, Any]) -> list[str]:
    expected = summary_metadata(cfg, plan, summary.get("gpu_id"))
    errors = []
    for key in (
        "run_id",
        "stage",
        "task_key",
        "task_group_key",
        "task_group_label",
        "suite",
        "task_id",
        "task_name",
        "execution_method",
        "added_delay_ms",
        "seed",
        "n_action_steps",
        "fixed_horizon",
        "repository_revision",
        "model_revision",
        "environment_fingerprint",
    ):
        if summary.get(key) != expected.get(key):
            errors.append(f"{key}={summary.get(key)!r}, expected {expected.get(key)!r}")
    if summary.get("episode_id") != plan.episode_id:
        errors.append(f"episode_id={summary.get('episode_id')!r}, expected {plan.episode_id!r}")
    if summary.get("strategy") != plan.execution_method:
        errors.append(
            f"strategy={summary.get('strategy')!r}, expected {plan.execution_method!r}"
        )
    return errors


def _filter_plans(plans: list[Stage0Plan], args: argparse.Namespace) -> list[Stage0Plan]:
    return [
        plan
        for plan in plans
        if (not args.task or plan.task_ref in args.task)
        and (not args.seed or plan.seed in args.seed)
        and (not args.method or plan.execution_method in args.method)
        and (not args.added_delay_ms or plan.added_delay_ms in args.added_delay_ms)
    ]


def _close_envs(env_cache: dict[str, Any]) -> None:
    for env in env_cache.values():
        close = getattr(env, "close", None)
        if callable(close):
            close()


def _latency_profile_for_plan(
    cfg: BenchmarkConfig, plan: Stage0Plan, *, refinement: bool
) -> LatencyProfile:
    profile_cfg = next(
        (profile for profile in cfg.latency_profiles if profile.name == plan.latency_profile),
        None,
    )
    if profile_cfg is not None:
        return LatencyProfile(
            profile_cfg.name,
            profile_cfg.use_measured_native_latency,
            profile_cfg.added_latency_ms,
        )
    if refinement and plan.added_delay_ms in REFINEMENT_DELAYS_MS:
        return LatencyProfile(plan.latency_profile, True, float(plan.added_delay_ms))
    raise ValueError(f"no latency profile configured for {plan.latency_profile}")


def run(
    cfg: BenchmarkConfig,
    plans: list[Stage0Plan],
    args: argparse.Namespace,
    *,
    refinement: bool = False,
) -> int:
    output_dir = cfg.output_dir
    for name in ("requests", "actions", "episodes", "summaries", "figures"):
        ensure_dir(output_dir / name)

    policy = None
    preprocessor = None
    postprocessor = None
    gpu_id = None
    env_cache: dict[str, Any] = {}
    try:
        for plan in plans:
            episode_path = output_dir / "episodes" / f"{plan.episode_id}.json"
            if args.resume and episode_path.exists() and not args.overwrite:
                existing = json.loads(episode_path.read_text())
                errors = _identity_errors(cfg, plan, existing)
                errors.extend(validate_episode(output_dir, plan.episode_id, existing))
                if not errors:
                    print(f"skip {plan.episode_id}: already completed and validated")
                    continue
                print(f"rerun {plan.episode_id}: prior artifact has {len(errors)} validation errors")

            if plan.task_ref not in env_cache:
                env_cache[plan.task_ref] = make_libero_env(
                    plan.task.suite,
                    plan.task.task_id,
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
            env = env_cache[plan.task_ref]
            task_info = get_task_info(env, plan.task.suite, plan.task.task_id)
            _assert_task(plan, task_info.task_name)

            if policy is None:
                policy, preprocessor, postprocessor = _load_policy_and_processors(cfg)
                gpu_id = _gpu_id()

            policy.config.rtc_config.enabled = plan.execution_method == "rtc"
            profile = _latency_profile_for_plan(cfg, plan, refinement=refinement)
            summary = run_episode(
                env=env,
                policy=policy,
                preprocessor=preprocessor,
                postprocessor=postprocessor,
                task_instruction=task_info.language_instruction,
                episode_id=plan.episode_id,
                strategy=plan.execution_method,
                latency_profile=profile,
                fixed_horizon=plan.fixed_horizon,
                output_dir=output_dir,
                seed=plan.seed,
                use_rtc=plan.execution_method == "rtc",
                rtc_execution_horizon=plan.fixed_horizon,
                request_threshold_actions=request_threshold_for_horizon(plan.fixed_horizon),
                device=cfg.device,
                summary_metadata=summary_metadata(cfg, plan, gpu_id),
            )
            errors = _identity_errors(cfg, plan, summary)
            errors.extend(validate_episode(output_dir, plan.episode_id, summary))
            if errors:
                summary["status"] = "invalid"
                summary["invalid_reason"] = " | ".join(errors)
                write_json(episode_path, summary)
                print(f"INVALID {plan.episode_id}: {summary['invalid_reason']}")
                return 1
            print(
                f"completed {plan.run_id} {plan.task_ref} {plan.execution_method} "
                f"+{plan.added_delay_ms}ms seed={plan.seed}: success={summary['success']}"
            )
    finally:
        _close_envs(env_cache)

    if refinement:
        from async_vla_benchmark.scripts.analyze_stage0_refinement import (
            build_stage0_refinement_artifacts,
        )

        return build_stage0_refinement_artifacts(
            cfg,
            output_dir,
            args.base_output_dir,
            require_complete=len(plans) == 18,
        )

    from async_vla_benchmark.scripts.analyze_stage0 import build_stage0_artifacts

    return build_stage0_artifacts(cfg, output_dir, require_complete=len(plans) == 96)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--refinement-25-75", action="store_true")
    parser.add_argument("--base-output-dir", type=Path)
    parser.add_argument("--task", action="append")
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--method", choices=("naive_async", "rtc"), action="append")
    parser.add_argument("--added-delay-ms", type=int, action="append")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.resume and args.overwrite:
        parser.error("--resume and --overwrite are mutually exclusive")

    cfg = load_config(args.config)
    validate_stage0_config(cfg)
    primary_output_dir = cfg.output_dir
    refinement = args.refinement_25_75
    if args.output_dir:
        cfg.output_dir = args.output_dir
    elif refinement:
        cfg.output_dir = primary_output_dir.parent / REFINEMENT_STAGE
    args.base_output_dir = args.base_output_dir or primary_output_dir
    plans = stage0_refinement_plans(cfg) if refinement else stage0_plans(cfg)
    selected = _filter_plans(plans, args)
    if not selected:
        parser.error("Stage 0 filters selected zero episodes")

    manifest_name = (
        "latency_refinement_manifest.csv" if refinement else "latency_calibration_manifest.csv"
    )
    manifest_path = cfg.output_dir / manifest_name
    rows = manifest_rows_for_plans(cfg, plans) if refinement else manifest_rows(cfg)
    write_csv(manifest_path, rows)
    label = "Stage 0 refinement" if refinement else "Stage 0"
    print(f"{label} preflight passed; manifest={manifest_path}; planned_episodes={len(plans)}")

    if args.dry_run:
        for plan in selected:
            print(json.dumps(plan_asdict(plan), sort_keys=True))
        print(f"selected_episodes={len(selected)}")
        return 0
    if args.manifest_only:
        return 0
    return run(cfg, selected, args, refinement=refinement)


if __name__ == "__main__":
    raise SystemExit(main())
