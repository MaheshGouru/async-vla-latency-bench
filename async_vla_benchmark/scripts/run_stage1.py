#!/usr/bin/env python3
"""Execute new Stage 1 rows from the frozen manifest (never Stage 0 reuse rows)."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import traceback
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import (
    get_max_episode_steps, get_task_info, make_libero_env, make_libero_plus_env,
)
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.metrics import percentile
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors
from async_vla_benchmark.benchmark.rtc import build_rtc_config, configure_rtc


def _bool(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def _column(path: Path, name: str) -> list[float]:
    try:
        import pandas as pd
        frame = pd.read_parquet(path)
        return [float(v) for v in frame[name].dropna().tolist()] if name in frame else []
    except Exception:
        return []


def _gpu() -> tuple[str, float | str]:
    try:
        import torch
        index = torch.cuda.current_device()
        physical = os.environ.get("STAGE1_PHYSICAL_GPU_ID", os.environ.get("CUDA_VISIBLE_DEVICES", "unknown"))
        return f"physical={physical};cuda={index}:{torch.cuda.get_device_name(index)}", torch.cuda.max_memory_allocated(index) / 1024**2
    except Exception:
        return "unknown", ""


def _environment_fingerprint() -> str:
    """Compact, stable runtime identity attached to every new Stage 1 row."""
    import importlib.metadata
    packages = {}
    for name in ("torch", "lerobot", "mujoco", "robosuite", "libero"):
        try: packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name] = "unknown"
    try:
        import torch
        cuda = torch.version.cuda or "none"
    except Exception:
        cuda = "unknown"
    return json.dumps({"python": platform.python_version(), "platform": platform.platform(), "cuda": cuda, "packages": packages}, sort_keys=True)


def _configure_libero_home(scene: str) -> None:
    """Prevent LIBERO's interactive first-run prompt and select the right fork."""
    if scene == "ood":
        roots = [Path(item) / "libero" / "libero" for item in os.environ.get("PYTHONPATH", "").split(os.pathsep) if item]
        root = next((item for item in roots if (item / "benchmark" / "task_classification.json").exists()), None)
        if root is None:
            raise FileNotFoundError("LIBERO-Plus root not found on PYTHONPATH")
    else:
        import libero
        root = Path(libero.__file__).parent / "libero"
    config = Path.home() / ".libero" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"benchmark_root: {root}\n" if scene == "id" else ""
    config.write_text(prefix +
        f"assets: {root / 'assets'}\n"
        f"bddl_files: {root / 'bddl_files'}\n"
        f"datasets: {root / '../datasets'}\n"
        f"init_states: {root / 'init_files'}\n")


def _episode_row(plan: dict[str, str], summary: dict, output: Path) -> dict:
    requests = output / "requests" / f"{plan['run_id']}.parquet"
    actions = output / "actions" / f"{plan['run_id']}.parquet"
    latencies = _column(requests, "measured_request_latency_ms")
    ages = _column(actions, "action_age_ms")
    delays = _column(requests, "delay_steps")
    queues = _column(actions, "queue_depth_before")
    gpu_id, peak = _gpu()
    pct = lambda values, p: percentile(values, p) if values else math.nan
    mean = lambda values: sum(values) / len(values) if values else math.nan
    identity = {key: plan.get(key, "") for key in (
        "run_id", "git_sha", "lerobot_git_sha", "libero_plus_git_sha", "model_revision",
        "task_key", "suite", "base_task_id", "base_task_name", "task_group",
        "scene_condition", "perturbation_key", "official_category", "mechanism_group",
        "classification_id", "api_task_index", "variant_name", "difficulty_level",
        "execution_method", "delay_condition", "added_delay_ms", "seed", "n_action_steps",
    )}
    return {**identity,
        "success": int(bool(summary["success"])), "episode_steps": summary["environment_steps"],
        "completion_fraction": "", "failure_mode": "success" if summary["success"] else ("timeout" if summary.get("timed_out") else "other"),
        "failure_notes": "", "request_latency_mean_ms": mean(latencies),
        "request_latency_p50_ms": pct(latencies, .5), "request_latency_p95_ms": pct(latencies, .95),
        "action_age_mean_ms": mean(ages), "action_age_p50_ms": pct(ages, .5),
        "action_age_p95_ms": pct(ages, .95), "action_age_max_ms": max(ages) if ages else math.nan,
        "logical_delay_steps_mean": mean(delays), "logical_delay_steps_p95": pct(delays, .95),
        "queue_occupancy_mean": mean(queues), "queue_occupancy_p95": pct(queues, .95),
        "underrun_count": summary["queue_underrun_steps"], "hold_count": summary["hold_action_steps"],
        "discard_count": summary["discarded_old_actions"], "num_policy_requests": summary["number_of_policy_requests"],
        "action_delta_mean": summary["mean_action_delta_l2"], "action_accel_mean": summary["mean_action_acceleration_l2"],
        "action_jerk_mean": summary["mean_action_jerk_l2"], "wall_clock_episode_s": summary["wall_clock_runtime_seconds"],
        "gpu_id": gpu_id, "gpu_peak_memory_mb": peak,
        "environment_fingerprint": _environment_fingerprint(),
        "source": "stage1_new", "status": "ok", "invalid_reason": "",
    }


def _merge(path: Path, rows: list[dict]) -> None:
    merged = {row["run_id"]: row for row in read_csv(path)} if path.exists() else {}
    merged.update({row["run_id"]: row for row in rows})
    ordered = [merged[key] for key in sorted(merged)]
    write_csv(path, ordered)


def main() -> int:
    # Never inherit Jupyter's module://matplotlib_inline backend into the
    # isolated ID/OOD execution environments.
    os.environ["MPLBACKEND"] = "Agg"
    native = Path.home() / "stage1-native"
    if native.exists():
        os.environ["MAGICK_HOME"] = str(native)
        os.environ["PATH"] = str(native / "bin") + os.pathsep + os.environ.get("PATH", "")
        os.environ["LD_LIBRARY_PATH"] = str(native / "lib") + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scene", choices=("id", "ood"), required=True,
                        help="run ID in standard image or OOD in LIBERO-Plus image")
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--task", action="append")
    parser.add_argument("--method", action="append")
    parser.add_argument("--delay", choices=("low", "high"), action="append")
    parser.add_argument("--perturbation", action="append")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    if cfg.policy_n_action_steps != 25:
        raise ValueError("Stage 1 requires policy_n_action_steps=25")
    _configure_libero_home(args.scene)
    plans = [row for row in read_csv(args.manifest) if row["scene_condition"] == args.scene and not _bool(row["reuse_stage0"])]
    for field, selected in (("seed", args.seed), ("task_key", args.task), ("execution_method", args.method), ("delay_condition", args.delay), ("perturbation_key", args.perturbation)):
        if selected:
            allowed = {str(value) for value in selected}
            plans = [row for row in plans if row[field] in allowed]
    if args.dry_run:
        for row in plans: print(row["run_id"])
        print(f"planned_episodes={len(plans)}")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    policy = load_pi05_policy(cfg.policy_checkpoint, cfg.checkpoint_revision, 25, cfg.device)
    configure_rtc(policy, build_rtc_config(
        execution_horizon=25,
        max_guidance_weight=cfg.rtc.max_guidance_weight,
        prefix_attention_schedule=cfg.rtc.prefix_attention_schedule,
    ))
    pre, post = load_pre_post_processors(policy, cfg.policy_checkpoint, cfg.checkpoint_revision)
    rows, failures = [], 0
    for index, plan in enumerate(plans, 1):
        episode_path = args.output_dir / "episodes" / f"{plan['run_id']}.json"
        try:
            if args.resume and episode_path.exists():
                summary = json.loads(episode_path.read_text())
            else:
                maker = make_libero_plus_env if args.scene == "ood" else make_libero_env
                env = maker(plan["suite"], int(plan["api_task_index"]), seed=int(plan["seed"]),
                    control_mode=cfg.control_mode, obs_type=cfg.obs_type, camera_name=cfg.camera_name,
                    observation_width=cfg.observation_width, observation_height=cfg.observation_height,
                    init_states=cfg.init_states, episode_length=cfg.episode_length, num_steps_wait=cfg.num_steps_wait)
                info = get_task_info(env, plan["suite"], int(plan["api_task_index"]))
                if info.task_name != plan["variant_name"]:
                    raise RuntimeError(f"task mismatch: {info.task_name!r} != {plan['variant_name']!r}")
                policy.config.rtc_config.enabled = plan["execution_method"] == "rtc"
                summary = run_episode(env, policy, pre, post, info.language_instruction,
                    episode_id=plan["run_id"], strategy=plan["execution_method"],
                    latency_profile=LatencyProfile("native" if plan["delay_condition"] == "low" else "native_plus_200", True, float(plan["added_delay_ms"])),
                    fixed_horizon=25, output_dir=args.output_dir, seed=int(plan["seed"]),
                    use_rtc=plan["execution_method"] == "rtc", rtc_execution_horizon=25,
                    request_threshold_actions=25, device=cfg.device)
            rows.append(_episode_row(plan, summary, args.output_dir))
            print(f"[{index}/{len(plans)}] {plan['run_id']}: success={summary['success']}")
        except Exception as exc:
            failures += 1
            print(f"[{index}/{len(plans)}] {plan['run_id']}: INVALID {exc}")
            if args.verbose: traceback.print_exc()
    if rows:
        _merge(args.output_dir / "stage1_episode_results.csv", rows)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
