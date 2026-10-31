#!/usr/bin/env python3
import argparse,hashlib
from pathlib import Path
from async_vla_benchmark.benchmark.experiment_a import _plan,validate_frozen_variants
from async_vla_benchmark.benchmark.logging import read_csv,write_csv
def main():
 p=argparse.ArgumentParser(); p.add_argument("--variants",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
 for x in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision"): p.add_argument("--"+x.replace("_","-"),required=True)
 a=p.parse_args(); variants=read_csv(a.variants); validate_frozen_variants(variants); frozen_hash=hashlib.sha256(a.variants.read_bytes()).hexdigest(); provenance={x:getattr(a,x) for x in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision")}; rows=[]
 for delay in (0,200): rows.append(_plan(provenance,None,"id",delay,999,frozen_hash))
 for variant in variants:
  for delay in (0,200): rows.append(_plan(provenance,variant,"ood",delay,999,frozen_hash))
 for row in rows: row["run_id"]+="__smoke"; row["output_path"]=f"episodes/{row['run_id']}.json"
 write_csv(a.output,rows); print("PASS smoke_manifest=8 seed=999 variants=3 analysis_seeds_used=0"); return 0
if __name__=="__main__": raise SystemExit(main())
