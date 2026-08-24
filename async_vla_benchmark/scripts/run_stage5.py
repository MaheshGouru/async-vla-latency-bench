#!/usr/bin/env python3
"""Run one serial scene shard of Stage 5A or 5B with the frozen OpenVLA-OFT policy."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import traceback
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env, make_libero_plus_env, resolve_episode_index
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.openvla_oft import OpenVLAOFTPolicy, verify_checkout, verify_snapshot, write_policy_provenance
from async_vla_benchmark.benchmark.stage5 import NATIVE_CHUNK_SIZE
from async_vla_benchmark.scripts.run_stage1 import _configure_libero_home, _environment_fingerprint, _episode_row, _merge
from async_vla_benchmark.scripts.run_stage3 import _artifact_state, _ensure_ood_native_prefix, _sha256


def _packages():
    import importlib.metadata as md, platform
    names = ("torch", "torchvision", "transformers", "tokenizers", "huggingface-hub", "tensorflow", "draccus", "libero", "robosuite")
    return {"python": platform.python_version(), **{name: (md.version(name) if _has(name) else None) for name in names}}


def _has(name):
    import importlib.metadata as md
    try:
        md.version(name)
        return True
    except md.PackageNotFoundError:
        return False


def _row(plan, summary, output, manifest_hash, spec_hash, unnorm_key, provenance):
    import pandas as pd
    row = _episode_row(plan, summary, output)
    requests = pd.read_parquet(output / "requests" / f"{plan['run_id']}.parquet")
    actions = pd.read_parquet(output / "actions" / f"{plan['run_id']}.parquet")
    measured = requests[requests["latency_profile"] != "ideal"]
    if measured.empty:
        raise RuntimeError("no non-startup requests")
    policy_actions = actions[actions["action_source"] == "policy"]
    row.update({
        **{k: v for k, v in plan.items() if k not in row},
        "n_action_steps": plan["configured_action_coverage"],
        "stage": plan["stage"],
        "stage_or_experiment_label": plan["stage_or_experiment_label"],
        "manifest_sha256": manifest_hash,
        "spec_sha256": spec_hash,
        "action_head_identity": provenance["action_head_identity"],
        "processor_identity": provenance["processor_identity"],
        "resolved_unnorm_key": unnorm_key,
        "measured_request_latency_ms": float(measured["measured_request_latency_ms"].mean()),
        "total_logical_latency_ms": float(measured["total_logical_latency_ms"].mean()),
        "logical_delay_steps": float(measured["logical_delay_steps"].mean()),
        "mean_action_age_ms": float(policy_actions["action_age_ms"].mean()) if not policy_actions.empty else float("nan"),
        "p95_action_age_ms": float(policy_actions["action_age_ms"].quantile(.95)) if not policy_actions.empty else float("nan"),
        "queue_underrun_steps": int(actions["is_queue_underrun"].sum()),
        "hold_action_steps": int(actions["is_hold_action"].sum()),
        "hold_action_fraction": float(actions["is_hold_action"].mean()),
        "num_policy_requests": len(measured),
        "startup_requests_excluded": int((requests["latency_profile"] == "ideal").sum()),
        "failure_class": "success" if summary["success"] else "genuine_task_failure",
        "environment_fingerprint": _environment_fingerprint(),
        "source": f"{plan['stage']}_new",
        "status": "ok_success" if summary["success"] else "ok_task_failure",
    })
    return row


def main():
    os.environ["MPLBACKEND"] = "Agg"
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=("a", "b"), required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--scene", choices=("id", "ood"), required=True)
    p.add_argument("--openvla-oft-checkout", type=Path, required=True)
    p.add_argument("--checkpoint-snapshot", type=Path, required=True)
    p.add_argument("--seed", type=int, action="append")
    p.add_argument("--task", action="append")
    p.add_argument("--coverage", type=int, action="append")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    _ensure_ood_native_prefix(args.scene)
    if args.scene == "ood":
        from wand.api import library as _wand_library  # noqa: F401

    verify_checkout(args.openvla_oft_checkout)
    verify_snapshot(args.checkpoint_snapshot)
    cfg = load_config(args.config)
    _configure_libero_home(args.scene)
    plans = [r for r in read_csv(args.manifest) if r.get("scene") == args.scene]
    if not plans:
        print(f"{args.scene}: manifest empty for this phase; nothing to do")
        return 0

    # Filter by phase based on the `stage` column.
    plans = [r for r in plans if ("stage5a" in r.get("stage", "") and args.phase == "a") or ("stage5b" in r.get("stage", "") and args.phase == "b")]
    if not plans:
        print(f"{args.scene}: no {args.phase} plans; nothing to do")
        return 0

    if args.seed:
        plans = [r for r in plans if int(r["seed"]) in set(args.seed)]
    if args.task:
        plans = [r for r in plans if r["task_key"] in set(args.task)]
    if args.coverage:
        plans = [r for r in plans if int(r["configured_action_coverage"]) in set(args.coverage)]

    plans.sort(key=lambda r: (r["task_key"], int(r["configured_action_coverage"]), int(r["added_delay_ms"]), int(r["seed"])))
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    results = output / f"stage5{args.phase}_episode_results.csv"
    manifest_hash = _sha256(args.manifest)
    spec_name = f"STAGE_5_{'A' if args.phase == 'a' else 'B'}_OPENVLA_OFT_*.md" if args.phase == "a" else "STAGE_5_OPENVLA_OFT_COVERAGE_CALIBRATION_AND_FINAL_REPLICATION.md"
    spec_files = list(Path(__file__).resolve().parents[2] / "docs" / "STAGE_5_OPENVLA_OFT_COVERAGE_CALIBRATION_AND_FINAL_REPLICATION.md")
    spec_path = next((f for f in spec_files if f.exists()), None)
    spec_hash = _sha256(spec_path) if spec_path and spec_path.exists() else ""
    existing = {r["run_id"] for r in read_csv(results)} if results.exists() else set()
    invalid = output / f"stage5{args.phase}_invalid_episodes.csv"
    if not invalid.exists():
        invalid.write_text("run_id,seed,failure_class,invalid_reason\n")
    pending = [r for r in plans if not args.resume or r["run_id"] not in existing or _artifact_state(output, r["run_id"]) != "valid"]
    if not pending:
        print(f"{args.scene} complete for phase {args.phase}; skipping model load")
        return 0

    import sys
    sys.path.insert(0, str(args.openvla_oft_checkout))
    policy = OpenVLAOFTPolicy(args.checkpoint_snapshot, args.openvla_oft_checkout)
    provenance = policy.provenance()
    write_policy_provenance(output / f"stage5{args.phase}_policy_provenance.json", policy, _packages())
    failures = 0
    for index, plan in enumerate(pending, 1):
        env = None
        try:
            unnorm = policy.set_suite(plan["suite"])
            maker = make_libero_plus_env if args.scene == "ood" else make_libero_env
            max_steps = 220 if plan["suite"] == "libero_spatial" else 520
            env = maker(
                plan["suite"], int(plan["api_task_index"]), seed=int(plan["seed"]), control_mode=cfg.control_mode,
                obs_type=cfg.obs_type, camera_name=cfg.camera_name, observation_width=cfg.observation_width,
                observation_height=cfg.observation_height, init_states=cfg.init_states, episode_length=max_steps,
                num_steps_wait=cfg.num_steps_wait, episode_index=0, reset_on_create=False,
            )
            if resolve_episode_index(env) != 0:
                raise RuntimeError("initialization did not resolve to index zero")
            info = get_task_info(env, plan["suite"], int(plan["api_task_index"]))
            if info.task_name != plan["variant_name"]:
                raise RuntimeError(f"task mismatch {info.task_name!r}")
            delay = int(plan["added_delay_ms"])
            coverage = int(plan["configured_action_coverage"])
            if coverage > NATIVE_CHUNK_SIZE:
                raise RuntimeError(f"coverage {coverage} exceeds audited native horizon {NATIVE_CHUNK_SIZE}")
            summary = run_episode(
                env, policy, None, policy.postprocess, info.language_instruction,
                episode_id=plan["run_id"], strategy="naive_async",
                latency_profile=LatencyProfile("native" if delay == 0 else "native_plus_200", True, float(delay)),
                fixed_horizon=coverage, output_dir=output, seed=int(plan["seed"]), use_rtc=False,
                request_threshold_actions=int(plan["request_threshold_actions"]), device=cfg.device,
            )
            for field in ("initialization_index_or_id", "initial_state_fingerprint", "initial_state_fingerprint_method"):
                if summary.get(field) != plan.get(field):
                    raise RuntimeError(f"reset identity mismatch {field}")
            _merge(results, [_row(plan, summary, output, manifest_hash, spec_hash, unnorm, provenance)])
            existing.add(plan["run_id"])
            print(f"[{index}/{len(pending)}] {plan['run_id']}: success={summary['success']}", flush=True)
        except Exception as exc:
            failures += 1
            _merge(invalid, [{"run_id": plan["run_id"], "seed": plan["seed"], "failure_class": "infrastructure_corruption", "invalid_reason": repr(exc)}])
            print(f"[{index}/{len(pending)}] {plan['run_id']}: INVALID {exc}", flush=True)
            if args.verbose:
                traceback.print_exc()
        finally:
            if env is not None and hasattr(env, "close"):
                env.close()
    del policy
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass
    return 1 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
