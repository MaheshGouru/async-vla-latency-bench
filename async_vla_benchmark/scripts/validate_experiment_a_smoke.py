#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv
def main():
 p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); rows=read_csv(a.manifest); errors=[]
 if len(rows)!=8 or {r["seed"] for r in rows}!={"999"}: errors.append("smoke manifest must contain 8 seed-999 rows")
 results=read_csv(a.output_dir/"experiment_a_episode_results.csv") if (a.output_dir/"experiment_a_episode_results.csv").exists() else []; by={r["run_id"]:r for r in results}
 for row in rows:
  result=by.get(row["run_id"])
  if not result or not result.get("status","").startswith("ok"): errors.append(f"{row['run_id']}: missing/invalid result")
  for folder,ext in (("episodes","json"),("requests","parquet"),("actions","parquet")):
   path=a.output_dir/folder/f"{row['run_id']}.{ext}"
   if not path.exists(): errors.append(f"{row['run_id']}: missing {folder}")
 report={"status":"pass" if not errors else "fail","episodes":len(rows),"seed":999,"analysis_seeds_used":False,"errors":errors}; (a.output_dir/"experiment_a_smoke_validation.json").write_text(json.dumps(report,indent=2)+"\n")
 if errors: print(*(f"ERROR: {e}" for e in errors),sep="\n"); return 1
 print("PASS: 8 seed-999 Experiment A smoke episodes; no analysis seeds used"); return 0
if __name__=="__main__": raise SystemExit(main())
