#!/usr/bin/env python3
"""Freeze reviewed Stage 4 candidates from complete Stage 3 results."""
import argparse
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage4 import ELIGIBLE_VARIANTS


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage3-results",type=Path,required=True)
    p.add_argument("--stage3-interactions",type=Path,required=True)
    p.add_argument("--candidate",action="append",default=[])
    p.add_argument("--selection-reason",required=True)
    p.add_argument("--confirm-reviewed",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    results=read_csv(args.stage3_results)
    if len(results)!=288 or len({r["run_id"] for r in results})!=288 or any(not r.get("status","").startswith("ok") for r in results):
        raise ValueError("Stage 3 must be complete and valid before Stage 4 selection")
    if not args.confirm_reviewed: raise ValueError("candidate replication must be reviewed explicitly")
    if not 1<=len(args.candidate)<=2: raise ValueError("choose one or two candidates")
    interactions=read_csv(args.stage3_interactions)
    h25={r["perturbation_key"]:r for r in interactions if r["configured_n_action_steps"]=="25" and r["analysis_status"]=="prespecified_confirmatory"}
    rows=[]
    for key in args.candidate:
        if key not in ELIGIBLE_VARIANTS or key not in h25: raise ValueError(f"not an eligible prespecified h25 candidate: {key}")
        variant=ELIGIBLE_VARIANTS[key]
        rows.append({
            "candidate_key":f'{variant["task_key"]}:{key}', "task_key":variant["task_key"],
            "perturbation_key":key, "classification_id":variant["classification_id"],
            "api_task_index":variant["api_task_index"], "variant_name":variant["variant_name"],
            "difficulty_level":variant["difficulty_level"],
            "stage3_analysis_status":"prespecified_confirmatory",
            "stage3_h25_interaction":h25[key]["interaction_I_h"],
            "stage3_h25_bootstrap95_low":h25[key]["paired_bootstrap95_low"],
            "stage3_h25_bootstrap95_high":h25[key]["paired_bootstrap95_high"],
            "selection_reason":args.selection_reason,
            "selection_frozen_before_vlash_outcomes":"True",
        })
    write_csv(args.output,rows)
    print(f"PASS: froze {len(rows)} reviewed prespecified Stage 4 candidate(s); no VLASH outcomes consulted")


if __name__=="__main__": raise SystemExit(main())
