#!/usr/bin/env python3
"""Run Stage 1: LIBERO-Plus perturbation families crossed with native/native+d* latency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from async_vla_benchmark.benchmark.config import BenchmarkConfig, load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_plus_env
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import ensure_dir, write_csv, write_json
from async_vla_benchmark.benchmark.ood_tasks import verify_task_id_mapping
from async_vla_benchmark.benchmark.queues import request_threshold_for_horizon
from async_vla_benchmark.benchmark.stage1 import (
    Stage1Plan,
    manifest_rows,
    plan_asdict,
    read_selected_high_delay,
    stage1_plans,
    summary_metadata,
    validate_stage1_config,
)
from async_vla_benchmark.scripts.run_benchmark import _load_policy_and_processors
from async_vla_benchmark.scripts.validate_results import validate_episode


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "stage1_libero_plus.yaml"


def _gpu_id() -> str | None:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(torch.cuda.current_device())
    except Exception:
        return None
    return None


def _filter_plans(plans: list[Stage1Plan], args: argparse.Namespace) -> list[Stage1Plan]:
    return [
        plan
        for plan in plans
        if (not args.task or plan.base_task_ref in args.task or plan.variant_task_ref in args.task)
        and (not args.seed or plan.seed in args.seed)
        and (not args.method or plan.execution_method in args.method)
        and (not args.perturbation or plan.perturbation.key in args.perturbation)
        and (not args.latency_condition or plan.latency_condition in args.latency_condition)
    ]


def _identity_errors(cfg: BenchmarkConfig, plan: Stage1Plan, summary: dict[str, Any]) -> list[str]:
    expected = summary_metadata(cfg, plan, summary.get("gpu_id"))
    errors = []
    for key in (
        "run_id",
        "stage",
        "task_key",
        "task_group_key",
        "task_group_label",
        "suite",
        "base_task_id",
        "base_task_name",
        "libero_plus_task_id",
        "libero_plus_task_name",
        "perturbation_key",
        "perturbation_category",
        "execution_method",
        "latency_condition",
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


def _close_envs(env_cache: dict[str, Any]) -> None:
    for env in env_cache.values():
        close = getattr(env, "close", None)
        if callable(close):
            close()


def _latency_profile_for_plan(plan: Stage1Plan) -> LatencyProfile:
    return LatencyProfile(plan.latency_profile, True, float(plan.added_delay_ms))


def run(cfg: BenchmarkConfig, plans: list[Stage1Plan], args: argparse.Namespace) -> int:
    output_dir = cfg.output_dir
    for name in ("requests", "actions", "episodes", "summaries", "figures"):
        ensure_dir(output_dir / name)

    policy = None
    preprocessor = None
    postprocessor = None
    gpu_id = None
    env_cache: dict[str, Any] = {}
    completed: list[dict[str, Any]] = []
    try:
        for plan in plans:
            episode_path = output_dir / "episodes" / f"{plan.episode_id}.json"
            if args.resume and episode_path.exists() and not args.overwrite:
                existing = json.loads(episode_path.read_text())
                errors = _identity_errors(cfg, plan, existing)
                errors.extend(validate_episode(output_dir, plan.episode_id, existing))
                if not errors:
                    print(f"skip {plan.episode_id}: already completed and validated")
                    completed.append(existing)
                    continue
                print(f"rerun {plan.episode_id}: prior artifact has {len(errors)} validation errors")

            env_key = f"{plan.variant_task_ref}:seed{plan.seed}"
            if env_key not in env_cache:
                env_cache[env_key] = make_libero_plus_env(
                    plan.task.suite,
                    plan.variant.task_id,
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
            task_info = get_task_info(env, plan.task.suite, plan.variant.task_id)
            if not verify_task_id_mapping(plan.task.suite, plan.variant, task_info.task_name):
                raise RuntimeError(
                    f"LIBERO-Plus mapping mismatch for {plan.variant_task_ref}: "
                    f"classification={plan.variant.name!r}, live={task_info.task_name!r}"
                )

            if policy is None:
                policy, preprocessor, postprocessor = _load_policy_and_processors(cfg)
                gpu_id = _gpu_id()

            policy.config.rtc_config.enabled = plan.execution_method == "rtc"
            summary = run_episode(
                env=env,
                policy=policy,
                preprocessor=preprocessor,
                postprocessor=postprocessor,
                task_instruction=task_info.language_instruction,
                episode_id=plan.episode_id,
                strategy=plan.execution_method,
                latency_profile=_latency_profile_for_plan(plan),
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
            completed.append(summary)
            print(
                f"completed {plan.run_id} {plan.variant_task_ref} {plan.perturbation.key} "
                f"{plan.execution_method} +{plan.added_delay_ms}ms seed={plan.seed}: "
                f"success={summary['success']}"
            )
    finally:
        _close_envs(env_cache)

    write_json(output_dir / "summaries" / "stage1_summaries.json", completed)
    write_csv(output_dir / "summaries" / "stage1_episodes.csv", completed)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--stage0-delay-selection-file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--task", action="append")
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--method", choices=("naive_async", "rtc"), action="append")
    parser.add_argument("--perturbation", action="append")
    parser.add_argument(
        "--latency-condition",
        choices=("native", "native_plus_dstar"),
        action="append",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.resume and args.overwrite:
        parser.error("--resume and --overwrite are mutually exclusive")

    cfg = load_config(args.config)
    validate_stage1_config(cfg)
    if args.output_dir:
        cfg.output_dir = args.output_dir
    assert cfg.stage1 is not None
    delay_file = args.stage0_delay_selection_file or Path(cfg.stage1.stage0_delay_selection_file)
    high_delay_ms = read_selected_high_delay(delay_file)

    plans = stage1_plans(cfg, high_delay_ms=high_delay_ms)
    selected = _filter_plans(plans, args)
    if not selected:
        parser.error("Stage 1 filters selected zero episodes")

    manifest_path = cfg.output_dir / "stage1_libero_plus_manifest.csv"
    write_csv(manifest_path, manifest_rows(cfg, plans))
    print(
        f"Stage 1 preflight passed; d*={high_delay_ms} ms; manifest={manifest_path}; "
        f"planned_episodes={len(plans)}; selected_episodes={len(selected)}"
    )

    if args.dry_run:
        for plan in selected:
            print(json.dumps(plan_asdict(plan), sort_keys=True))
        return 0
    if args.manifest_only:
        return 0
    return run(cfg, selected, args)


if __name__ == "__main__":
    raise SystemExit(main())
