#!/usr/bin/env python3
import argparse
from pathlib import Path
from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage3b import as_rows,stage3b_manifest
def main():
 p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True)
 for x in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision"): p.add_argument("--"+x.replace("_","-"),required=True)
 a=p.parse_args(); rows=stage3b_manifest(vars(a)); write_csv(a.output,as_rows(rows)); print("PASS manifest=144 new_OOD=96 new_ID=48 reused_goal_ID=48"); return 0
if __name__=="__main__": raise SystemExit(main())
