#!/usr/bin/env python3
"""Run one scene shard of the frozen Stage 3 matrix serially."""
from __future__ import annotations
import argparse, gc, hashlib, json, os, traceback
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env, make_libero_plus_env, resolve_episode_index
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors
from async_vla_benchmark.benchmark.rtc import build_rtc_config, configure_rtc
from async_vla_benchmark.benchmark.stage3 import HORIZONS
from async_vla_benchmark.scripts.run_stage1 import _configure_libero_home, _environment_fingerprint, _episode_row, _merge


def _ensure_ood_native_prefix(scene):
    if scene != "ood": return
    native = Path.home() / "stage1-native"
    if native.exists() and os.environ.get("STAGE3_NATIVE_REEXEC") != str(native):
        environment = os.environ.copy(); environment["STAGE3_NATIVE_REEXEC"] = str(native)
        environment["MAGICK_HOME"] = str(native)
        environment["PATH"] = str(native / "bin") + os.pathsep + environment.get("PATH", "")
        environment["LD_LIBRARY_PATH"] = str(native / "lib") + os.pathsep + environment.get("LD_LIBRARY_PATH", "")
        os.execve(os.sys.executable, [os.sys.executable, *os.sys.argv], environment)


def _select(rows, field, selected):
    if not selected: return rows
    allowed = {str(v) for v in selected}; return [r for r in rows if r[field] in allowed]


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_state(output, run_id):
    episode = output / "episodes" / f"{run_id}.json"
    requests = output / "requests" / f"{run_id}.parquet"
    actions = output / "actions" / f"{run_id}.parquet"
    if not all(path.exists() for path in (episode, requests, actions)):
        return "missing"
    try:
        summary = json.loads(episode.read_text())
        if summary.get("episode_id") != run_id:
            return "invalid"
        import pandas as pd
        if pd.read_parquet(requests).empty or pd.read_parquet(actions).empty:
            return "invalid"
    except Exception:
        return "invalid"
    return "valid"


def _stage3_row(plan, summary, output, manifest_sha256, spec_sha256, stage_label="stage3"):
    row = _episode_row({**plan, "n_action_steps": plan["configured_n_action_steps"]}, summary, output)
    import pandas as pd
    frame = pd.read_parquet(output / "requests" / f"{plan['run_id']}.parquet")
    measured = frame[frame["latency_profile"] != "ideal"]
    if measured.empty: raise RuntimeError("episode has no non-startup policy requests")
    h = int(plan["configured_n_action_steps"])
    errors = measured["rtc_inference_delay_error_steps"]
    absolute_errors = errors.abs()
    row.update({
        "stage": stage_label, "stage_or_experiment_label": stage_label,
        "analysis_status": plan["analysis_status"],
        "manifest_sha256": manifest_sha256, f"{stage_label}_spec_sha256": spec_sha256,
        "spec_sha256": spec_sha256,
        "frozen_variant_csv_sha256": plan.get("frozen_variant_csv_sha256", ""),
        "checkpoint_id": plan["checkpoint_id"], "runner_commit": plan["runner_commit"],
        "environment_version": plan["environment_version"], "base_task_id": plan["base_task_id"],
        "base_task_name": plan["base_task_name"], "task_id": plan["task_id"], "task_name": plan["task_name"],
        "configured_n_action_steps": h, "prediction_horizon_actions": int(summary["prediction_horizon_actions"]),
        "rtc_execution_horizon": int(plan["rtc_execution_horizon"]),
        "request_threshold_actions": int(plan["request_threshold_actions"]), "control_period_ms": 50.0,
        "request_latency_mean_ms": measured["measured_request_latency_ms"].mean(),
        "request_latency_p50_ms": measured["measured_request_latency_ms"].quantile(.5),
        "request_latency_p95_ms": measured["measured_request_latency_ms"].quantile(.95),
        "logical_delay_steps_mean": measured["logical_delay_steps"].mean(),
        "logical_delay_steps_p95": measured["logical_delay_steps"].quantile(.95),
        "num_policy_requests": len(measured),
        "rtc_inference_delay_mismatch_rate_nonstartup": (errors != 0).mean(),
        "rtc_mean_signed_inference_delay_error_steps_nonstartup": errors.mean(),
        "rtc_mean_absolute_inference_delay_error_steps_nonstartup": absolute_errors.mean(),
        "rtc_p95_absolute_inference_delay_error_steps_nonstartup": absolute_errors.quantile(.95),
        "rtc_max_absolute_inference_delay_error_steps_nonstartup": absolute_errors.max(),
        "coverage_ratio_added": (int(plan["added_delay_ms"]) / 50.0) / h,
        "coverage_ratio_total_mean": measured["coverage_ratio_total"].mean(),
        "rtc_mean_frozen_prefix_steps": measured["rtc_frozen_prefix_actions"].mean(),
        "rtc_mean_guided_overlap_steps": measured["rtc_guided_actions"].mean(),
        "rtc_mean_fresh_suffix_steps": measured["rtc_fresh_suffix_actions"].mean(),
        "startup_requests_excluded_from_primary_latency": int((frame["latency_profile"] == "ideal").sum()),
        "failure_class": "success" if summary["success"] else "genuine_task_failure",
        "initialization_index_or_id": summary["initialization_index_or_id"],
        "initial_state_fingerprint": summary["initial_state_fingerprint"],
        "initial_state_fingerprint_method": summary["initial_state_fingerprint_method"],
        "requested_initialization_index": plan.get("requested_initialization_index", 0),
        "resolved_initialization_index_or_id": plan.get("resolved_initialization_index_or_id", 0),
        "source": f"{stage_label}_new", "environment_fingerprint": _environment_fingerprint(),
    })
    return row


def main():
    os.environ["MPLBACKEND"] = "Agg"
    p = argparse.ArgumentParser(); p.add_argument("--config", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True); p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--scene", choices=("id", "ood"), required=True); p.add_argument("--horizon", type=int, action="append")
    p.add_argument("--delay", type=int, action="append"); p.add_argument("--seed", type=int, action="append")
    p.add_argument("--task", action="append"); p.add_argument("--perturbation", action="append")
    p.add_argument("--exclude-posthoc", action="store_true"); p.add_argument("--resume", action="store_true")
    p.add_argument("--stage-label", choices=("stage3","stage3b","experiment_a"), default="stage3")
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--verbose", action="store_true"); args = p.parse_args()
    _ensure_ood_native_prefix(args.scene)
    if args.scene == "ood":
        from wand.api import library as _wand_library  # noqa: F401
    cfg = load_config(args.config); _configure_libero_home(args.scene)
    plans = [r for r in read_csv(args.manifest) if r["scene"] == args.scene]
    plans = _select(plans, "configured_n_action_steps", args.horizon); plans = _select(plans, "added_delay_ms", args.delay)
    plans = _select(plans, "seed", args.seed); plans = _select(plans, "task_key", args.task)
    plans = _select(plans, "perturbation_key", args.perturbation)
    if args.exclude_posthoc: plans = [r for r in plans if r["analysis_status"] != "posthoc_replication"]
    plans.sort(key=lambda r: (int(r["configured_n_action_steps"]), r["task_key"], r["perturbation_key"], int(r["added_delay_ms"]), int(r["seed"])))
    if args.dry_run:
        print(*(r["run_id"] for r in plans), sep="\n"); print(f"planned_episodes={len(plans)}"); return 0
    args.output_dir.mkdir(parents=True, exist_ok=True); results_path = args.output_dir / f"{args.stage_label}_episode_results.csv"
    manifest_sha256 = _sha256(args.manifest)
    spec_name = {
        "stage3":"STAGE_3_OOD_HORIZON_CONFIRMATION.md",
        "stage3b":"STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md",
        "experiment_a":"EXPERIMENT_A_OBJECT_LAYOUT_VARIANT_GENERALIZATION.md",
    }[args.stage_label]
    spec_path = Path(__file__).resolve().parents[2] / "docs" / spec_name
    spec_sha256 = _sha256(spec_path)
    existing = {r["run_id"] for r in read_csv(results_path)} if results_path.exists() else set()
    invalid_path = args.output_dir / f"{args.stage_label}_invalid_episodes.csv"
    if not invalid_path.exists():
        invalid_path.write_text("run_id,seed,failure_class,invalid_reason\n")
    failures = completed = 0
    for horizon in [h for h in HORIZONS if any(int(r["configured_n_action_steps"]) == h for r in plans)]:
        pending = [r for r in plans if int(r["configured_n_action_steps"]) == horizon]
        if args.resume: pending = [r for r in pending if r["run_id"] not in existing or _artifact_state(args.output_dir, r["run_id"]) != "valid"]
        if not pending: print(f"[h={horizon}] complete; skipping model load"); continue
        policy = load_pi05_policy(cfg.policy_checkpoint, cfg.checkpoint_revision, horizon, cfg.device)
        configure_rtc(policy, build_rtc_config(execution_horizon=horizon, max_guidance_weight=cfg.rtc.max_guidance_weight, prefix_attention_schedule=cfg.rtc.prefix_attention_schedule))
        pre, post = load_pre_post_processors(policy, cfg.policy_checkpoint, cfg.checkpoint_revision)
        for plan in pending:
            completed += 1; env = None
            try:
                episode_path = args.output_dir/"episodes"/f"{plan['run_id']}.json"
                if args.resume and _artifact_state(args.output_dir, plan["run_id"]) == "valid": summary = json.loads(episode_path.read_text())
                else:
                    maker = make_libero_plus_env if args.scene == "ood" else make_libero_env
                    env = maker(plan["suite"], int(plan["api_task_index"]), seed=int(plan["seed"]), control_mode=cfg.control_mode, obs_type=cfg.obs_type, camera_name=cfg.camera_name, observation_width=cfg.observation_width, observation_height=cfg.observation_height, init_states=cfg.init_states, episode_length=cfg.episode_length, num_steps_wait=cfg.num_steps_wait, episode_index=0, reset_on_create=args.stage_label!="experiment_a")
                    resolved_index = resolve_episode_index(env)
                    if resolved_index != 0: raise RuntimeError(f"requested episode_index=0 resolved as {resolved_index}")
                    info = get_task_info(env, plan["suite"], int(plan["api_task_index"]))
                    if info.task_name != plan["variant_name"]: raise RuntimeError(f"task mismatch: {info.task_name!r} != {plan['variant_name']!r}")
                    delay = int(plan["added_delay_ms"])
                    summary = run_episode(env, policy, pre, post, info.language_instruction, episode_id=plan["run_id"], strategy="rtc", latency_profile=LatencyProfile("native" if delay == 0 else "native_plus_200", True, float(delay)), fixed_horizon=horizon, output_dir=args.output_dir, seed=int(plan["seed"]), use_rtc=True, rtc_execution_horizon=horizon, request_threshold_actions=horizon, device=cfg.device)
                summary["prediction_horizon_actions"] = int(policy.config.chunk_size)
                for field in ("initialization_index_or_id", "initial_state_fingerprint", "initial_state_fingerprint_method"):
                    if summary.get(field) != plan.get(field): raise RuntimeError(f"reset identity mismatch {field}: {summary.get(field)!r} != {plan.get(field)!r}")
                _merge(results_path, [_stage3_row(plan, summary, args.output_dir, manifest_sha256, spec_sha256,args.stage_label)]); existing.add(plan["run_id"])
                print(f"[{completed}/{len(plans)}] {plan['run_id']}: success={summary['success']}", flush=True)
            except Exception as exc:
                failures += 1
                _merge(invalid_path, [{"run_id":plan["run_id"], "seed":plan["seed"], "failure_class":"infrastructure_corruption", "invalid_reason":repr(exc)}])
                print(f"[{completed}/{len(plans)}] {plan['run_id']}: INVALID {exc}", flush=True)
                if args.verbose: traceback.print_exc()
            finally:
                if env is not None and hasattr(env, "close"): env.close()
        del policy, pre, post; gc.collect()
        try:
            import torch; torch.cuda.empty_cache()
        except Exception: pass
    return 1 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
