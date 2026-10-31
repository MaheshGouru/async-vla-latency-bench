#!/usr/bin/env python3
import argparse
from pathlib import Path
from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage3b import _row,as_rows
def main():
 p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True)
 for x in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision"): p.add_argument("--"+x.replace("_","-"),required=True)
 a=p.parse_args(); provenance=vars(a); rows=[]
 for scene in ("id","ood"):
  for delay in (0,200): rows.append(_row(provenance,"spatial_transport",scene,25,delay,999))
 # Smoke IDs are isolated from analysis outputs and use an explicit suffix.
 for r in rows: object.__setattr__(r,"run_id",r.run_id+"__smoke"); object.__setattr__(r,"output_path",f"episodes/{r.run_id}.json")
 write_csv(a.output,as_rows(rows)); print("PASS smoke_manifest=4 seed=999 analysis_seeds_used=0"); return 0
if __name__=="__main__": raise SystemExit(main())
