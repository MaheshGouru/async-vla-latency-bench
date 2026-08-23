#!/usr/bin/env python3
import argparse, hashlib, json
from collections import defaultdict
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.stage4 import DELAYS_MS, EXECUTION_METHOD, POLICY_FAMILY, SEEDS, TASKS, validate_manifest


def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--allow-incomplete",action="store_true"); a=p.parse_args(); errors=[]
    rows=read_csv(a.manifest)
    try: validate_manifest(rows)
    except Exception as exc: errors.append(str(exc))
    groups=defaultdict(list)
    for r in rows: groups[(r["task_key"],r["scene_condition"],r["variant_name"],r["seed"])].append(r)
    if len(groups)!=32: errors.append(f"expected 32 delay-pair groups, got {len(groups)}")
    for key,group in groups.items():
        if len(group)!=2 or {int(r["added_delay_ms"]) for r in group}!=set(DELAYS_MS): errors.append(f"{key}: incomplete delay pair")
        identities={(r["requested_initialization_index"],r["resolved_initialization_index_or_id"],r["initialization_index_or_id"],r["initial_state_fingerprint_method"],r["initial_state_fingerprint"]) for r in group}
        if len(identities)!=1 or any(not x or str(x).startswith("PENDING") for x in next(iter(identities),("",)*5)): errors.append(f"{key}: unresolved/unpaired reset")
    result_path=a.output_dir/"stage4_episode_results.csv"; results=read_csv(result_path) if result_path.exists() else []; by_id={r["run_id"]:r for r in results}; manifest_ids={r["run_id"] for r in rows}; missing=manifest_ids-set(by_id); invalid=[]
    for run_id,result in by_id.items():
        if run_id not in manifest_ids: errors.append(f"unexpected result {run_id}"); continue
        plan=next(r for r in rows if r["run_id"]==run_id)
        if not result.get("status","").startswith("ok"): invalid.append(run_id)
        required={"policy_family":POLICY_FAMILY,"execution_method":EXECUTION_METHOD,"native_chunk_size":"8","configured_action_coverage":"8","request_threshold_actions":"4","requested_initialization_index":"0","resolved_initialization_index_or_id":"0"}
        for field,expected in required.items():
            if str(result.get(field))!=expected: errors.append(f"{run_id}: {field} mismatch")
        for field in ("variant_name","classification_id","api_task_index","initial_state_fingerprint","checkpoint_revision","openvla_oft_git_sha"):
            if str(result.get(field))!=str(plan.get(field)): errors.append(f"{run_id}: {field} differs from manifest")
        for folder,ext in (("episodes","json"),("requests","parquet"),("actions","parquet")):
            path=a.output_dir/folder/f"{run_id}.{ext}"
            if not path.exists(): errors.append(f"{run_id}: missing {folder} artifact")
        try:
            import pandas as pd
            req=pd.read_parquet(a.output_dir/"requests"/f"{run_id}.parquet"); act=pd.read_parquet(a.output_dir/"actions"/f"{run_id}.parquet")
            measured=req[req["latency_profile"]!="ideal"]
            if len(req[req["latency_profile"]=="ideal"])!=1: errors.append(f"{run_id}: startup request count != 1")
            if measured.empty or set(measured["configured_n_action_steps"])!={8}: errors.append(f"{run_id}: request coverage mismatch")
            if set(measured["request_threshold_actions"])!={4}: errors.append(f"{run_id}: request threshold mismatch")
            if req["rtc_inference_delay_steps"].notna().any(): errors.append(f"{run_id}: RTC guidance appeared")
            if act.empty: errors.append(f"{run_id}: empty action artifact")
        except Exception as exc: errors.append(f"{run_id}: malformed parquet: {exc}")
    if missing and not a.allow_incomplete: errors.append(f"{len(missing)} missing results")
    if invalid: errors.append(f"{len(invalid)} invalid results")
    provenance=a.output_dir/"stage4_policy_provenance.json"
    if results and not provenance.exists(): errors.append("missing stage4_policy_provenance.json")
    report={"status":"fail" if errors else ("incomplete_allowed" if missing else "pass"),"manifest_rows":len(rows),"result_rows":len(results),"missing_rows":len(missing),"invalid_rows":len(invalid),"manifest_sha256":hashlib.sha256(a.manifest.read_bytes()).hexdigest(),"results_sha256":hashlib.sha256(result_path.read_bytes()).hexdigest() if result_path.exists() else None,"errors":sorted(set(errors))}
    (a.output_dir/"stage4_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"manifest={len(rows)} results={len(results)} missing={len(missing)} invalid={len(invalid)}")
    if errors: print(*(f"ERROR: {e}" for e in sorted(set(errors))),sep="\n"); return 1
    print("Stage 4 validation passed"); return 0


if __name__=="__main__": raise SystemExit(main())
