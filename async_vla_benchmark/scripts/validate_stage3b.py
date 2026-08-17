#!/usr/bin/env python3
import argparse,json
from collections import defaultdict
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.stage3b import HORIZONS,ADDED_DELAYS_MS,SEEDS,VARIANTS
def main():
 p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--reuse-audit",type=Path,required=True); p.add_argument("--allow-incomplete",action="store_true"); a=p.parse_args(); errors=[]
 rows=read_csv(a.manifest); ids={r["run_id"] for r in rows}
 if len(rows)!=144 or len(ids)!=144: errors.append("manifest must contain 144 unique new rows")
 if sum(r["scene"]=="ood" for r in rows)!=96 or sum(r["scene"]=="id" for r in rows)!=48: errors.append("new rows must be 96 OOD + 48 spatial ID")
 if any(r["task_key"]=="goal_drawer" and r["scene"]=="id" for r in rows): errors.append("goal ID was rerun")
 if any(r["task_key"]=="long_stove_moka" for r in rows): errors.append("long task was rerun")
 expected={(k,str(v["classification_id"]),str(v["api_task_index"]),v["variant_name"],str(v["difficulty_level"])) for k,v in VARIANTS.items()}
 actual={(r["task_key"],r["classification_id"],r["api_task_index"],r["variant_name"],r["difficulty_level"]) for r in rows if r["scene"]=="ood"}
 if actual!=expected: errors.append("exact frozen object-layout variants changed")
 groups=defaultdict(list)
 for r in rows: groups[(r["task_key"],r["scene"],r["variant_name"],r["seed"])].append(r)
 if len(groups)!=24: errors.append(f"expected 24 new pairing groups, got {len(groups)}")
 for key,g in groups.items():
  if {(int(r["configured_n_action_steps"]),int(r["added_delay_ms"])) for r in g}!={(h,d) for h in HORIZONS for d in ADDED_DELAYS_MS}: errors.append(f"{key}: incomplete six-cell block")
  identity={(r["initialization_index_or_id"],r["initial_state_fingerprint_method"],r["initial_state_fingerprint"]) for r in g}
  if len(identity)!=1 or any(not x or x.startswith("PENDING") for x in next(iter(identity),("","",""))): errors.append(f"{key}: unresolved pairing identity")
 reuse=read_csv(a.reuse_audit) if a.reuse_audit.exists() else []
 if len(reuse)!=48 or len({r["run_id"] for r in reuse})!=48 or any(r["reuse_status"]!="valid_stage3_goal_id_control" for r in reuse): errors.append("reuse audit must contain 48 valid original goal-ID rows")
 results_path=a.output_dir/"stage3b_episode_results.csv"; results=read_csv(results_path) if results_path.exists() else []; by={r["run_id"]:r for r in results}; missing=ids-set(by); invalid=[r["run_id"] for r in results if not r.get("status","").startswith("ok")]
 for run_id in ids&set(by):
  plan=next(r for r in rows if r["run_id"]==run_id); result=by[run_id]
  for f in ("initialization_index_or_id","initial_state_fingerprint","initial_state_fingerprint_method"):
   if result.get(f)!=plan.get(f): errors.append(f"{run_id}: {f} mismatch")
  for folder,ext in (("episodes","json"),("requests","parquet"),("actions","parquet")):
   path=a.output_dir/folder/f"{run_id}.{ext}"
   if not path.exists(): errors.append(f"{run_id}: missing {folder}")
   elif ext=="json":
    try: json.loads(path.read_text())
    except Exception: errors.append(f"{run_id}: invalid episode JSON")
 if missing and not a.allow_incomplete: errors.append(f"{len(missing)} missing results")
 if invalid: errors.append(f"{len(invalid)} invalid results")
 print(f"manifest=144 results={len(results)} missing={len(missing)} invalid={len(invalid)} reused_goal_id={len(reuse)}")
 if errors: print(*(f"ERROR: {x}" for x in errors),sep="\n"); return 1
 print("Stage 3B validation passed"); return 0
if __name__=="__main__": raise SystemExit(main())
