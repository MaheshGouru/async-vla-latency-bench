#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage4 import as_rows, stage4_manifest


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidates",type=Path,required=True); p.add_argument("--compatibility-report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    for name in ("git_sha","lerobot_git_sha","libero_plus_git_sha","model_revision","vlash_revision","vlash_checkpoint_id"):
        p.add_argument("--"+name.replace("_","-"),required=True)
    args=p.parse_args(); report=json.loads(args.compatibility_report.read_text())
    if report.get("status")!="PASS": raise ValueError("official VLASH compatibility gate has not passed")
    if report.get("vlash_revision")!=args.vlash_revision: raise ValueError("VLASH revision differs from compatibility audit")
    provenance=dict(vars(args)); provenance["vlash_repository"]=report["official_repository"]
    candidates=read_csv(args.candidates); rows=stage4_manifest(candidates,provenance)
    write_csv(args.output,as_rows(rows))
    tasks={r["task_key"] for r in candidates}; logical=40*len(candidates)
    print(f"PASS: Stage 4 manifest physical={len(rows)} logical_candidate_references={logical} candidates={len(candidates)} shared_id_tasks={len(tasks)}")


if __name__=="__main__": raise SystemExit(main())
