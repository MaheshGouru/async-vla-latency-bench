#!/usr/bin/env python3
"""Create an isolated non-analysis Stage 3 smoke manifest on seed 999."""
import argparse
from dataclasses import replace
from pathlib import Path

from async_vla_benchmark.benchmark.logging import write_csv
from async_vla_benchmark.benchmark.stage3 import as_rows, stage3_manifest


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--git-sha",required=True); parser.add_argument("--lerobot-git-sha",required=True)
    parser.add_argument("--libero-plus-git-sha",required=True); parser.add_argument("--model-revision",required=True)
    args=parser.parse_args()
    provenance={key:getattr(args,key.replace("-","_")) for key in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision")}
    source=stage3_manifest(provenance); chosen=[]
    for row in source:
        if row.task_key!="goal_drawer" or row.seed!=14: continue
        if row.scene=="ood" and row.perturbation_key!="light_conditions": continue
        run_id=row.run_id.rsplit("__s",1)[0]+"__s999__smoke"
        chosen.append(replace(row,run_id=run_id,seed=999,analysis_status="smoke_only",
            initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
            initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
            output_path=f"episodes/{run_id}.json"))
    if len(chosen)!=12 or len({r.run_id for r in chosen})!=12: raise ValueError("smoke manifest must contain 12 unique rows")
    write_csv(args.output,as_rows(chosen)); print("PASS smoke manifest=12 seed=999 analysis_status=smoke_only")
    return 0


if __name__=="__main__": raise SystemExit(main())
