#!/usr/bin/env python3
"""Fail-closed validator for Stage 3 New.

Flags:
  --allow-incomplete   skip missing-results check (use after manifest freeze)
  --smoke              validate 18-row seed-999 smoke run
  --require-scene id   require only the ID scene to be complete (use before OOD launch)
"""
from __future__ import annotations
import argparse, json, math
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.stage3_new import (
    ADDED_DELAYS_MS, CANDIDATES, HORIZONS, SEEDS, _OLD_SEEDS,
    _EXPECTED_ID, _EXPECTED_OOD, _EXPECTED_TOTAL,
)

RESULTS_CSV = "stage3_new_episode_results.csv"


def _check_manifest(manifest: list[dict], errors: list[str], smoke: bool) -> None:
    expected_total = 18 if smoke else _EXPECTED_TOTAL
    expected_id    = 6  if smoke else _EXPECTED_ID
    expected_ood   = 12 if smoke else _EXPECTED_OOD

    if len(manifest) != expected_total:
        errors.append(f"manifest must contain {expected_total} rows; got {len(manifest)}")
    if len({r["run_id"] for r in manifest}) != len(manifest):
        errors.append("duplicate run_ids in manifest")

    seed_set = {int(r["seed"]) for r in manifest}
    if smoke:
        if seed_set != {999}:
            errors.append(f"smoke manifest must use only seed 999; got {seed_set}")
    else:
        if seed_set != set(SEEDS):
            errors.append(f"seeds must be exactly {min(SEEDS)}..{max(SEEDS)}")
        if seed_set & _OLD_SEEDS:
            errors.append("manifest contains forbidden old Stage 3/3B seeds (14-21)")

    if {int(r["added_delay_ms"]) for r in manifest} != set(ADDED_DELAYS_MS):
        errors.append("wrong delay conditions in manifest")
    if any(r["execution_method"] != "rtc" for r in manifest):
        errors.append("Stage 3 New must be RTC-only")

    n_id  = sum(1 for r in manifest if r["scene"] == "id")
    n_ood = sum(1 for r in manifest if r["scene"] == "ood")
    if n_id != expected_id:
        errors.append(f"expected {expected_id} ID rows; got {n_id}")
    if n_ood != expected_ood:
        errors.append(f"expected {expected_ood} OOD rows; got {n_ood}")

    if not smoke:
        expected_cands = {c["candidate_key"] for c in CANDIDATES}
        actual_cands   = {r["candidate_key"] for r in manifest if r["scene"] == "ood"}
        if actual_cands != expected_cands:
            errors.append(f"candidate key mismatch: missing={expected_cands - actual_cands} "
                          f"extra={actual_cands - expected_cands}")

        expected_variants = {
            (str(c["classification_id"]), str(c["api_task_index"]),
             c["variant_name"], str(c["difficulty_level"]))
            for c in CANDIDATES
        }
        actual_variants = {
            (r["classification_id"], r["api_task_index"],
             r["variant_name"], r["difficulty_level"])
            for r in manifest if r["scene"] == "ood"
        }
        if actual_variants != expected_variants:
            errors.append("frozen OOD variant identities changed")

        # Pairing: each (task, variant, seed, scene) block must share one fingerprint.
        groups: dict = defaultdict(list)
        for r in manifest:
            key = (r["task_key"], r["variant_name"], r["seed"], r["scene"])
            groups[key].append(r)
        for key, group in groups.items():
            fps = {(r.get("initialization_index_or_id", ""),
                    r.get("initial_state_fingerprint_method", ""),
                    r.get("initial_state_fingerprint", ""))
                   for r in group}
            if any(v.startswith("PENDING_") for triple in fps for v in triple):
                continue  # not yet resolved; --allow-incomplete handles this
            if len(fps) != 1:
                errors.append(f"inconsistent reset fingerprints for {key}")


def _check_results(manifest: list[dict], results: list[dict],
                   errors: list[str], allow_incomplete: bool,
                   smoke: bool, require_scene: str | None) -> None:
    by_id = {r["run_id"]: r for r in results}

    result_seeds = {int(r["seed"]) for r in results}
    if result_seeds & _OLD_SEEDS:
        errors.append("results contain forbidden old Stage 3/3B seeds (14-21)")

    if smoke:
        if len(results) != 18:
            errors.append(f"smoke run must produce 18 results; got {len(results)}")
        if result_seeds != {999}:
            errors.append(f"smoke results must all use seed 999; got {result_seeds}")
        if not all(r.get("status", "").startswith("ok") for r in results):
            errors.append("some smoke episodes did not complete successfully")
        return

    if require_scene:
        expected_n   = _EXPECTED_ID if require_scene == "id" else _EXPECTED_OOD
        scene_results = [r for r in results
                         if r.get("scene_condition") == require_scene
                         or r.get("scene") == require_scene]
        missing = [r["run_id"] for r in manifest
                   if r["scene"] == require_scene and r["run_id"] not in by_id]
        if len(scene_results) != expected_n:
            errors.append(f"--require-scene {require_scene}: expected {expected_n} results; "
                          f"got {len(scene_results)}")
        if missing:
            errors.append(f"{len(missing)} missing {require_scene} result rows")
        return

    missing = [r["run_id"] for r in manifest if r["run_id"] not in by_id]
    if missing and not allow_incomplete:
        errors.append(f"{len(missing)} missing result rows")
    if len({r["run_id"] for r in results}) != len(results):
        errors.append("duplicate run_ids in results")

    required_fields = (
        "stage", "candidate_key", "analysis_status",
        "checkpoint_id", "runner_commit", "environment_version",
        "manifest_sha256", "stage3_new_spec_sha256",
        "initialization_index_or_id", "initial_state_fingerprint",
        "initial_state_fingerprint_method",
        "configured_n_action_steps", "prediction_horizon_actions",
        "rtc_execution_horizon", "request_threshold_actions",
        "control_period_ms", "request_latency_mean_ms",
        "logical_delay_steps_mean", "coverage_ratio_added",
        "coverage_ratio_total_mean",
        "rtc_mean_frozen_prefix_steps", "rtc_mean_guided_overlap_steps",
        "rtc_mean_fresh_suffix_steps",
        "rtc_inference_delay_mismatch_rate_nonstartup",
        "rtc_mean_absolute_inference_delay_error_steps_nonstartup",
        "environment_fingerprint",
    )
    for plan in manifest:
        run_id = plan["run_id"]
        if run_id not in by_id:
            continue
        result = by_id[run_id]
        for field in required_fields:
            if result.get(field, "") == "":
                errors.append(f"{run_id}: missing required field {field!r}")
        for field in ("initialization_index_or_id",
                      "initial_state_fingerprint",
                      "initial_state_fingerprint_method"):
            if result.get(field) != plan.get(field):
                errors.append(f"{run_id}: {field} mismatch between manifest and result")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--allow-incomplete", action="store_true")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--require-scene", choices=("id", "ood"))
    args = p.parse_args()

    errors: list[str] = []
    manifest = read_csv(args.manifest)
    _check_manifest(manifest, errors, smoke=args.smoke)

    results_path = args.output_dir / RESULTS_CSV
    results = read_csv(results_path) if results_path.exists() else []

    if results or not args.allow_incomplete:
        _check_results(manifest, results, errors,
                       allow_incomplete=args.allow_incomplete,
                       smoke=args.smoke,
                       require_scene=args.require_scene)

    # Per-artifact file checks.
    try:
        import pandas as pd
        has_pandas = True
    except ImportError:
        has_pandas = False

    by_result = {r["run_id"]: r for r in results}
    for plan in manifest:
        run_id = plan["run_id"]
        if run_id not in by_result:
            continue
        for folder, ext in (("episodes", "json"), ("actions", "parquet"), ("requests", "parquet")):
            fpath = args.output_dir / folder / f"{run_id}.{ext}"
            if not fpath.exists():
                errors.append(f"{run_id}: missing {folder}/{run_id}.{ext}")
            elif ext == "json":
                try:
                    json.loads(fpath.read_text())
                except Exception:
                    errors.append(f"{run_id}: invalid episode JSON")
            elif ext == "parquet" and folder == "requests" and has_pandas:
                try:
                    frame    = pd.read_parquet(fpath)
                    measured = frame[frame["latency_profile"] != "ideal"]
                    if measured.empty:
                        errors.append(f"{run_id}: no non-startup policy requests")
                    h = int(plan["configured_n_action_steps"])
                    for _, req in measured.iterrows():
                        expected_steps = math.ceil(
                            float(req["total_logical_latency_ms"])
                            / float(req["control_period_ms"])
                        )
                        if int(req["logical_delay_steps"]) != expected_steps:
                            errors.append(f"{run_id}: logical delay mismatch")
                            break
                        if int(req["rtc_configured_execution_horizon"]) != h:
                            errors.append(f"{run_id}: RTC horizon mismatch")
                            break
                except Exception as exc:
                    errors.append(f"{run_id}: parquet read error: {exc}")

    n_results = len(results)
    n_missing = sum(1 for r in manifest if r["run_id"] not in by_result)
    n_invalid = sum(1 for r in results if not r.get("status", "").startswith("ok"))
    tag = ("smoke" if args.smoke
           else f"require_scene={args.require_scene}" if args.require_scene
           else "full")
    print(f"[{tag}] manifest={len(manifest)} results={n_results} "
          f"missing={n_missing} invalid={n_invalid}")

    if errors:
        print(*[f"ERROR: {e}" for e in errors], sep="\n")
        return 1
    print("Stage 3 New validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
