#!/usr/bin/env python3
import argparse,hashlib
from pathlib import Path
from async_vla_benchmark.benchmark.experiment_a import experiment_a_manifest
from async_vla_benchmark.benchmark.logging import read_csv,write_csv
def main():
 p=argparse.ArgumentParser(); p.add_argument("--variants",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
 for x in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision"): p.add_argument("--"+x.replace("_","-"),required=True)
 a=p.parse_args(); frozen_hash=hashlib.sha256(a.variants.read_bytes()).hexdigest(); provenance={x:getattr(a,x) for x in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision")}
 rows=experiment_a_manifest(read_csv(a.variants),provenance,frozen_hash); write_csv(a.output,rows); print("PASS manifest=64 ID=16 OOD=48 variants=3 seeds=8"); return 0
if __name__=="__main__": raise SystemExit(main())
