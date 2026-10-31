#!/usr/bin/env python3
import argparse,hashlib,json
from collections import defaultdict
from pathlib import Path
from async_vla_benchmark.benchmark.experiment_a import ANALYSIS_STATUS,DELAYS,HORIZON,SEEDS,validate_frozen_variants,validate_manifest
from async_vla_benchmark.benchmark.logging import read_csv
def main():
 p=argparse.ArgumentParser(); p.add_argument("--variants",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--allow-incomplete",action="store_true"); a=p.parse_args(); errors=[]
 variants=read_csv(a.variants); rows=read_csv(a.manifest); frozen_hash=hashlib.sha256(a.variants.read_bytes()).hexdigest()
 try: validate_frozen_variants(variants); validate_manifest(rows,variants,frozen_hash)
 except Exception as exc: errors.append(str(exc))
 groups=defaultdict(list)
 for r in rows: groups[(r["scene_condition"],r["variant_name"],r["seed"])].append(r)
 if len(groups)!=32: errors.append(f"expected 32 paired seed groups, got {len(groups)}")
 for key,g in groups.items():
  if {int(r["added_delay_ms"]) for r in g}!=set(DELAYS) or len(g)!=2: errors.append(f"{key}: incomplete Native/+200 pair")
  identities={(r["initialization_index_or_id"],r["initial_state_fingerprint_method"],r["initial_state_fingerprint"],r.get("requested_initialization_index"),r.get("resolved_initialization_index_or_id")) for r in g}
  if len(identities)!=1 or any(not x or str(x).startswith("PENDING") for x in next(iter(identities),("",)*5)): errors.append(f"{key}: unresolved or unpaired initialization")
  elif next(iter(identities))[3:] not in (("0","0"),(0,0)): errors.append(f"{key}: initialization is not requested/resolved zero")
 result_path=a.output_dir/"experiment_a_episode_results.csv"; results=read_csv(result_path) if result_path.exists() else []; by={r["run_id"]:r for r in results}; ids={r["run_id"] for r in rows}; missing=ids-set(by); invalid=[]
 for run_id,result in by.items():
  if run_id not in ids: errors.append(f"unexpected result {run_id}"); continue
  if not result.get("status","").startswith("ok"): invalid.append(run_id)
  plan=next(r for r in rows if r["run_id"]==run_id)
  for field in ("initialization_index_or_id","initial_state_fingerprint","initial_state_fingerprint_method","frozen_variant_csv_sha256"):
   if result.get(field)!=plan.get(field): errors.append(f"{run_id}: {field} mismatch")
  if result.get("stage_or_experiment_label")!="experiment_a" or result.get("analysis_status")!=ANALYSIS_STATUS: errors.append(f"{run_id}: provenance label mismatch")
  if result.get("requested_initialization_index")!="0" or result.get("resolved_initialization_index_or_id")!="0": errors.append(f"{run_id}: initialization index is not zero")
  for folder,ext in (("episodes","json"),("requests","parquet"),("actions","parquet")):
   path=a.output_dir/folder/f"{run_id}.{ext}"
   if not path.exists(): errors.append(f"{run_id}: missing {folder}")
   elif ext=="json":
    try: json.loads(path.read_text())
    except Exception: errors.append(f"{run_id}: invalid episode JSON")
 unresolved=[]; invalid_path=a.output_dir/"experiment_a_invalid_episodes.csv"
 if invalid_path.exists(): unresolved=[r["run_id"] for r in read_csv(invalid_path) if r.get("run_id") not in by or not by[r["run_id"]].get("status","").startswith("ok")]
 if missing and not a.allow_incomplete: errors.append(f"{len(missing)} missing results")
 if invalid: errors.append(f"{len(invalid)} invalid result rows")
 if unresolved: errors.append(f"{len(set(unresolved))} unresolved infrastructure failures")
 report={"status":"fail" if errors else ("incomplete_allowed" if missing else "pass"),"manifest_rows":len(rows),"result_rows":len(results),"missing_rows":len(missing),"invalid_rows":len(invalid),"variant_rows":len(variants),"manifest_sha256":hashlib.sha256(a.manifest.read_bytes()).hexdigest(),"frozen_variants_sha256":frozen_hash,"results_sha256":hashlib.sha256(result_path.read_bytes()).hexdigest() if result_path.exists() else None,"errors":sorted(set(errors))}
 a.output_dir.mkdir(parents=True,exist_ok=True); (a.output_dir/"experiment_a_validation.json").write_text(json.dumps(report,indent=2)+"\n")
 print(f"manifest={len(rows)} results={len(results)} missing={len(missing)} invalid={len(invalid)} variants={len(variants)}")
 if errors: print(*(f"ERROR: {e}" for e in sorted(set(errors))),sep="\n"); return 1
 print("Experiment A validation passed"); return 0
if __name__=="__main__": raise SystemExit(main())
