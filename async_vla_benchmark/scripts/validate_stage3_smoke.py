#!/usr/bin/env python3
import argparse, json
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.scripts.run_stage3 import _artifact_state


def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--json-output",type=Path); args=p.parse_args()
    manifest=read_csv(args.manifest); results=read_csv(args.output_dir/"stage3_episode_results.csv")
    assert len(manifest)==12 and len({r["run_id"] for r in manifest})==12
    assert {r["seed"] for r in manifest}=={"999"} and {r["analysis_status"] for r in manifest}=={"smoke_only"}
    groups=defaultdict(list)
    for r in manifest: groups[(r["scene"],r["variant_name"])].append(r)
    assert len(groups)==2 and all(len(g)==6 for g in groups.values())
    for group in groups.values():
        assert len({(r["initialization_index_or_id"],r["initial_state_fingerprint_method"],r["initial_state_fingerprint"]) for r in group})==1
    assert len(results)==12 and {r["run_id"] for r in results}=={r["run_id"] for r in manifest}
    assert all(_artifact_state(args.output_dir,r["run_id"])=="valid" for r in manifest)
    summary=[]
    for r in sorted(results,key=lambda x:(x["scene_condition"],int(x["configured_n_action_steps"]),int(x["added_delay_ms"]))):
        summary.append({"run_id":r["run_id"],"scene":r["scene_condition"],
            "configured_n_action_steps":r["configured_n_action_steps"],
            "added_delay_ms":r["added_delay_ms"],"success":r["success"],
            "analysis_status":r["analysis_status"],
            "initial_state_fingerprint":r["initial_state_fingerprint"]})
    analysis=args.output_dir/"analysis"; analysis.mkdir(exist_ok=True); write_csv(analysis/"stage3_seed999_smoke_summary.csv",summary)
    json_output = args.json_output or (Path.home()/"stage3"/"stage3_smoke_validation.json")
    json_output.parent.mkdir(parents=True,exist_ok=True)
    json_output.write_text(json.dumps({"validation_passed":True,"analysis_status":"smoke_only",
            "seed":999,"manifest_rows":12,"result_rows":12,"unique_result_run_ids":12,
            "id_rows":sum(r["scene"]=="id" for r in manifest),"ood_rows":sum(r["scene"]=="ood" for r in manifest),
            "artifact_triplets_valid":12,"analysis_seed_used":False},indent=2)+"\n")
    print("PASS: seed-999 reset → inference → artifacts → validation → smoke analysis; no analysis seeds used")
    return 0


if __name__=="__main__": raise SystemExit(main())
