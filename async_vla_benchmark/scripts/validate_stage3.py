#!/usr/bin/env python3
import argparse, json, math
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.stage3 import ADDED_DELAYS_MS, HORIZONS, OOD_VARIANTS, SEEDS


def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--allow-incomplete",action="store_true"); args=p.parse_args()
    manifest=read_csv(args.manifest); errors=[]
    if len(manifest)!=288 or len({r["run_id"] for r in manifest})!=288: errors.append("manifest must contain 288 unique rows")
    condition_keys={(r["scene"],r["task_key"],r["variant_name"],r["configured_n_action_steps"],r["added_delay_ms"],r["seed"]) for r in manifest}
    if len(condition_keys)!=288: errors.append("duplicate scene/task/variant/horizon/delay/seed conditions")
    if sum(r["analysis_status"]=="prespecified_confirmatory" for r in manifest)!=240: errors.append("primary analysis must contain 240 rows")
    if sum(r["analysis_status"]=="posthoc_replication" for r in manifest)!=48: errors.append("post-hoc analysis must contain 48 rows")
    if {int(r["configured_n_action_steps"]) for r in manifest}!=set(HORIZONS): errors.append("wrong horizons")
    if {int(r["added_delay_ms"]) for r in manifest}!=set(ADDED_DELAYS_MS): errors.append("wrong delays")
    if {int(r["seed"]) for r in manifest}!=set(SEEDS): errors.append("wrong seeds")
    if any(r["execution_method"]!="rtc" for r in manifest): errors.append("Stage 3 must be RTC-only")
    if sum(r["scene"]=="id" for r in manifest)!=96 or sum(r["scene"]=="ood" for r in manifest)!=192: errors.append("wrong ID/OOD counts")
    expected_variants={(str(v["classification_id"]),str(v["api_task_index"]),v["variant_name"],str(v["difficulty_level"])) for v in OOD_VARIANTS}
    actual_variants={(r["classification_id"],r["api_task_index"],r["variant_name"],r["difficulty_level"]) for r in manifest if r["scene"]=="ood"}
    if actual_variants!=expected_variants: errors.append("exact frozen OOD variants do not match Stage 1 identities")
    groups=defaultdict(list)
    for r in manifest: groups[(r["task_key"],r["variant_name"],r["seed"],r["scene"])].append(r)
    if len(groups)!=48: errors.append(f"expected 48 pairing groups, got {len(groups)}")
    for key,group in groups.items():
        cells={(int(r["configured_n_action_steps"]),int(r["added_delay_ms"])) for r in group}
        identities={(r.get("initialization_index_or_id",""),r.get("initial_state_fingerprint_method",""),r.get("initial_state_fingerprint","")) for r in group}
        if len(group)!=6 or cells!={(h,d) for h in HORIZONS for d in ADDED_DELAYS_MS}: errors.append(f"{key}: incomplete paired block")
        if len(identities)!=1 or any(not x or x.startswith("PENDING_") for x in next(iter(identities),())): errors.append(f"{key}: unresolved reset identity")
    results_path=args.output_dir/"stage3_episode_results.csv"; results=read_csv(results_path) if results_path.exists() else []; by_id={r["run_id"]:r for r in results}
    missing=[r["run_id"] for r in manifest if r["run_id"] not in by_id]; invalid=[r["run_id"] for r in results if not r.get("status","").startswith("ok")]
    required=("stage","analysis_status","checkpoint_id","runner_commit","environment_version","manifest_sha256","stage3_spec_sha256","initialization_index_or_id","initial_state_fingerprint","initial_state_fingerprint_method","configured_n_action_steps","prediction_horizon_actions","rtc_execution_horizon","request_threshold_actions","control_period_ms","request_latency_mean_ms","logical_delay_steps_mean","coverage_ratio_added","coverage_ratio_total_mean","rtc_mean_frozen_prefix_steps","rtc_mean_guided_overlap_steps","rtc_mean_fresh_suffix_steps","rtc_inference_delay_mismatch_rate_nonstartup","rtc_mean_signed_inference_delay_error_steps_nonstartup","rtc_mean_absolute_inference_delay_error_steps_nonstartup","rtc_p95_absolute_inference_delay_error_steps_nonstartup","rtc_max_absolute_inference_delay_error_steps_nonstartup","environment_fingerprint")
    try: import pandas as pd
    except ImportError: pd=None; errors.append("pandas is required for request validation")
    for plan in manifest:
        run_id=plan["run_id"]
        if run_id not in by_id: continue
        result=by_id[run_id]
        for field in required:
            if result.get(field,"")=="": errors.append(f"{run_id}: missing {field}")
        for field in ("initialization_index_or_id","initial_state_fingerprint","initial_state_fingerprint_method"):
            if result.get(field)!=plan.get(field): errors.append(f"{run_id}: {field} mismatch")
        request_path=args.output_dir/"requests"/f"{run_id}.parquet"
        if not request_path.exists(): errors.append(f"{run_id}: missing requests")
        elif pd is not None:
            frame=pd.read_parquet(request_path); measured=frame[frame["latency_profile"]!="ideal"]
            if measured.empty: errors.append(f"{run_id}: no non-startup requests")
            for _,request in measured.iterrows():
                expected=math.ceil(float(request["total_logical_latency_ms"])/float(request["control_period_ms"])); h=int(plan["configured_n_action_steps"])
                if int(request["logical_delay_steps"])!=expected: errors.append(f"{run_id}: logical delay mismatch")
                if int(request["rtc_configured_execution_horizon"])!=h or int(request["request_threshold_actions"])!=h: errors.append(f"{run_id}: RTC horizon/threshold mismatch")
                if not math.isclose(float(request["coverage_ratio_total"]),expected/h,abs_tol=1e-9): errors.append(f"{run_id}: coverage mismatch")
        for folder,ext in (("episodes","json"),("actions","parquet")):
            path=args.output_dir/folder/f"{run_id}.{ext}"
            if not path.exists(): errors.append(f"{run_id}: missing {folder}")
            elif ext=="json":
                try: json.loads(path.read_text())
                except Exception: errors.append(f"{run_id}: invalid episode JSON")
    if missing and not args.allow_incomplete: errors.append(f"{len(missing)} missing result rows")
    if invalid: errors.append(f"{len(invalid)} invalid result rows")
    print(f"manifest=288 results={len(results)} missing={len(missing)} invalid={len(invalid)}")
    if errors:
        print(*(f"ERROR: {e}" for e in errors),sep="\n"); return 1
    print("Stage 3 validation passed"); return 0


if __name__=="__main__": raise SystemExit(main())
