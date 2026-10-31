#!/usr/bin/env python3
"""Run the frozen Stage 2 matrix serially on one GPU."""

from __future__ import annotations

import argparse
import gc
import json
import os
import traceback
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors
from async_vla_benchmark.benchmark.rtc import build_rtc_config, configure_rtc
from async_vla_benchmark.benchmark.stage2 import HORIZONS
from async_vla_benchmark.scripts.run_stage1 import (
    _configure_libero_home, _environment_fingerprint, _episode_row, _merge,
)


def _select(rows, field, selected):
    if not selected:
        return rows
    allowed = {str(value) for value in selected}
    return [row for row in rows if row[field] in allowed]


def _stage2_row(plan: dict[str, str], summary: dict, output: Path) -> dict:
    row = _episode_row({
        **plan,
        "base_task_id": plan["api_task_index"],
        "base_task_name": plan["variant_name"],
        "perturbation_key": "id",
        "official_category": "ID",
        "mechanism_group": "id",
        "classification_id": "",
        "difficulty_level": "",
        "n_action_steps": plan["configured_n_action_steps"],
    }, summary, output)
    # Primary Stage 2 timing excludes the ideal startup request. That request is
    # retained in the canonical parquet so startup behavior remains auditable.
    import pandas as pd
    frame = pd.read_parquet(output / "requests" / f"{plan['run_id']}.parquet")
    measured = frame[frame["latency_profile"] != "ideal"]
    if measured.empty:
        raise RuntimeError("episode has no non-startup policy requests")
    h = int(plan["configured_n_action_steps"])
    row.update({
        "request_latency_mean_ms": measured["measured_request_latency_ms"].mean(),
        "request_latency_p50_ms": measured["measured_request_latency_ms"].quantile(.5),
        "request_latency_p95_ms": measured["measured_request_latency_ms"].quantile(.95),
        "logical_delay_steps_mean": measured["logical_delay_steps"].mean(),
        "logical_delay_steps_p95": measured["logical_delay_steps"].quantile(.95),
        "num_policy_requests": len(measured),
    })
    row.update({
        "stage": "stage2",
        "analysis_status": "posthoc_sensitivity",
        "checkpoint_id": plan["checkpoint_id"],
        "runner_commit": plan["runner_commit"],
        "environment_version": plan["environment_version"],
        "base_task_id": plan["base_task_id"],
        "base_task_name": plan["base_task_name"],
        "task_id": plan["task_id"],
        "task_name": plan["task_name"],
        "initialization_index_or_id": summary["initialization_index_or_id"],
        "initial_state_fingerprint": summary["initial_state_fingerprint"],
        "initial_state_fingerprint_method": summary["initial_state_fingerprint_method"],
        "configured_n_action_steps": h,
        "prediction_horizon_actions": int(summary["prediction_horizon_actions"]),
        "rtc_execution_horizon": int(plan["rtc_execution_horizon"]),
        "request_threshold_actions": int(plan["request_threshold_actions"]),
        "control_period_ms": 50.0,
        "coverage_ratio_added": (int(plan["added_delay_ms"]) / 50.0) / h,
        "coverage_ratio_total_mean": measured["coverage_ratio_total"].mean(),
        "rtc_mean_frozen_prefix_steps": measured["rtc_frozen_prefix_actions"].mean(),
        "rtc_mean_guided_overlap_steps": measured["rtc_guided_actions"].mean(),
        "rtc_mean_fresh_suffix_steps": measured["rtc_fresh_suffix_actions"].mean(),
        "startup_requests_excluded_from_primary_latency": int((frame["latency_profile"] == "ideal").sum()),
        "source": "stage2_new",
        "environment_fingerprint": _environment_fingerprint(),
    })
    return row


def main() -> int:
    os.environ["MPLBACKEND"] = "Agg"
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--horizon", type=int, action="append")
    parser.add_argument("--delay", type=int, action="append")
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--task", action="append")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    _configure_libero_home("id")
    plans = read_csv(args.manifest)
    plans = _select(plans, "configured_n_action_steps", args.horizon)
    plans = _select(plans, "added_delay_ms", args.delay)
    plans = _select(plans, "seed", args.seed)
    plans = _select(plans, "task_key", args.task)
    plans.sort(key=lambda r: (int(r["configured_n_action_steps"]), r["task_key"], int(r["added_delay_ms"]), int(r["seed"])))
    if args.dry_run:
        for row in plans:
            print(row["run_id"])
        print(f"planned_episodes={len(plans)}")
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    completed = 0
    results_path = args.output_dir / "stage2_local_sensitivity_episode_results.csv"
    existing_results = {row["run_id"] for row in read_csv(results_path)} if results_path.exists() else set()
    def artifacts_exist(run_id: str) -> bool:
        return all((args.output_dir / folder / f"{run_id}.{suffix}").exists() for folder, suffix in (
            ("episodes", "json"), ("requests", "parquet"), ("actions", "parquet")
        ))
    selected_horizons = [h for h in HORIZONS if any(int(p["configured_n_action_steps"]) == h for p in plans)]
    for horizon in selected_horizons:
        pending = [p for p in plans if int(p["configured_n_action_steps"]) == horizon]
        if args.resume:
            pending = [
                p for p in pending
                if p["run_id"] not in existing_results or not artifacts_exist(p["run_id"])
            ]
        if not pending:
            print(f"[h={horizon}] complete; skipping model load")
            continue
        policy = load_pi05_policy(cfg.policy_checkpoint, cfg.checkpoint_revision, horizon, cfg.device)
        configure_rtc(policy, build_rtc_config(
            execution_horizon=horizon,
            max_guidance_weight=cfg.rtc.max_guidance_weight,
            prefix_attention_schedule=cfg.rtc.prefix_attention_schedule,
        ))
        pre, post = load_pre_post_processors(policy, cfg.policy_checkpoint, cfg.checkpoint_revision)
        for plan in pending:
            completed += 1
            env = None
            try:
                episode_path = args.output_dir / "episodes" / f"{plan['run_id']}.json"
                if args.resume and artifacts_exist(plan["run_id"]):
                    summary = json.loads(episode_path.read_text())
                else:
                    env = make_libero_env(
                        plan["suite"], int(plan["api_task_index"]), seed=int(plan["seed"]),
                        control_mode=cfg.control_mode, obs_type=cfg.obs_type, camera_name=cfg.camera_name,
                        observation_width=cfg.observation_width, observation_height=cfg.observation_height,
                        init_states=cfg.init_states, episode_length=cfg.episode_length,
                        num_steps_wait=cfg.num_steps_wait,
                    )
                    info = get_task_info(env, plan["suite"], int(plan["api_task_index"]))
                    if info.task_name != plan["variant_name"]:
                        raise RuntimeError(f"task mismatch: {info.task_name!r} != {plan['variant_name']!r}")
                    delay = int(plan["added_delay_ms"])
                    summary = run_episode(
                        env, policy, pre, post, info.language_instruction,
                        episode_id=plan["run_id"], strategy="rtc",
                        latency_profile=LatencyProfile("native" if delay == 0 else f"native_plus_{delay}", True, float(delay)),
                        fixed_horizon=horizon, output_dir=args.output_dir, seed=int(plan["seed"]),
                        use_rtc=True, rtc_execution_horizon=horizon,
                        request_threshold_actions=horizon, device=cfg.device,
                    )
                prediction_horizon = getattr(policy.config, "chunk_size", None)
                if prediction_horizon is None:
                    raise RuntimeError("policy.config.chunk_size unavailable; cannot determine prediction horizon")
                summary["prediction_horizon_actions"] = int(prediction_horizon)
                for field in (
                    "initialization_index_or_id", "initial_state_fingerprint",
                    "initial_state_fingerprint_method",
                ):
                    if summary.get(field) != plan.get(field):
                        raise RuntimeError(
                            f"reset identity mismatch for {field}: "
                            f"actual={summary.get(field)!r} frozen={plan.get(field)!r}"
                        )
                _merge(results_path, [_stage2_row(plan, summary, args.output_dir)])
                existing_results.add(plan["run_id"])
                print(f"[{completed}/{len(plans)}] {plan['run_id']}: success={summary['success']}", flush=True)
            except Exception as exc:
                failures += 1
                print(f"[{completed}/{len(plans)}] {plan['run_id']}: INVALID {exc}", flush=True)
                if args.verbose:
                    traceback.print_exc()
            finally:
                if env is not None and hasattr(env, "close"):
                    env.close()
        del policy, pre, post
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
