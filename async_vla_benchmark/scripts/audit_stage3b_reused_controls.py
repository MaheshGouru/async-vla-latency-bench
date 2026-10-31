#!/usr/bin/env python3
import argparse
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv,write_csv
from async_vla_benchmark.benchmark.stage3b import HORIZONS,ADDED_DELAYS_MS,SEEDS
def main():
 p=argparse.ArgumentParser(); p.add_argument("--stage3-manifest",type=Path,required=True); p.add_argument("--stage3-results",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
 manifest=read_csv(a.stage3_manifest); results={r["run_id"]:r for r in read_csv(a.stage3_results)}
 rows=[r for r in manifest if r["task_key"]=="goal_drawer" and r["scene"]=="id"]
 expected={(h,d,s) for h in HORIZONS for d in ADDED_DELAYS_MS for s in SEEDS}; actual={(int(r["configured_n_action_steps"]),int(r["added_delay_ms"]),int(r["seed"])) for r in rows}
 if len(rows)!=48 or actual!=expected: raise ValueError("Stage 3 goal-ID control block is incomplete")
 audit=[]
 for plan in rows:
  result=results.get(plan["run_id"])
  if not result or not result.get("status","").startswith("ok"): raise ValueError(f"invalid reused control {plan['run_id']}")
  for field in ("checkpoint_id","configured_n_action_steps","added_delay_ms","seed","initialization_index_or_id","initial_state_fingerprint","initial_state_fingerprint_method"):
   if str(result.get(field,""))!=str(plan.get(field,"")): raise ValueError(f"{plan['run_id']}: {field} mismatch")
  audit.append({"run_id":plan["run_id"],"reuse_status":"valid_stage3_goal_id_control","original_stage":"stage3","task_key":"goal_drawer","scene":"id","configured_n_action_steps":plan["configured_n_action_steps"],"added_delay_ms":plan["added_delay_ms"],"seed":plan["seed"],"initialization_index_or_id":plan["initialization_index_or_id"],"initial_state_fingerprint":plan["initial_state_fingerprint"],"source_results":str(a.stage3_results)})
 write_csv(a.output,audit); print("PASS: audited 48 reusable Stage 3 goal-ID controls without new run IDs"); return 0
if __name__=="__main__": raise SystemExit(main())
