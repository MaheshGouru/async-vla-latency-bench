#!/usr/bin/env python3
import argparse
from dataclasses import asdict, replace
from pathlib import Path
from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage4 import TASKS, _plan


def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True); p.add_argument("--git-sha",required=True); p.add_argument("--libero-plus-git-sha",required=True); a=p.parse_args()
    provenance=vars(a); rows=[]
    for task in TASKS:
        for scene in ("id","ood"):
            row=_plan(provenance,task,scene,0,999)
            rows.append(asdict(replace(row,run_id=row.run_id+"__smoke",output_path=f"episodes/{row.run_id}__smoke.json",analysis_status="nonanalysis_smoke")))
    write_csv(a.output,rows); print("PASS: frozen four-row seed-999 Stage 4 smoke manifest"); return 0


if __name__=="__main__": raise SystemExit(main())
