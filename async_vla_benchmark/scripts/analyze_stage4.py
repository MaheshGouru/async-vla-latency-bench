#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage4 import TASKS, paired_interaction_values
from async_vla_benchmark.scripts.analyze_stage3 import paired_cluster_bootstrap, wilson


def main():
    p=argparse.ArgumentParser(); p.add_argument("--results",type=Path,required=True); p.add_argument("--validation",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
    validation=json.loads(a.validation.read_text())
    if validation.get("status")!="pass": raise ValueError("Stage 4 analysis requires passing validation")
    rows=read_csv(a.results)
    if len(rows)!=64 or len({r["run_id"] for r in rows})!=64: raise ValueError("Stage 4 analysis requires 64 unique results")
    a.output_dir.mkdir(parents=True,exist_ok=True); four=[]; interactions=[]
    for task in TASKS:
        record={"task_key":task}
        for scene in ("id","ood"):
            for delay,label in ((0,"native"),(200,"plus_200")):
                cell=[r for r in rows if r["task_key"]==task and r["scene_condition"]==scene and int(r["added_delay_ms"])==delay]
                successes=sum(int(r["success"]) for r in cell); low,high=wilson(successes,len(cell)); prefix=f"{scene}_{label}"
                record.update({prefix+"_successes":successes,prefix+"_trials":len(cell),prefix+"_rate":successes/len(cell),prefix+"_wilson95_low":low,prefix+"_wilson95_high":high})
        paired=paired_interaction_values(rows,task); interaction=(record["ood_plus_200_rate"]-record["ood_native_rate"])-(record["id_plus_200_rate"]-record["id_native_rate"]); low,high=paired_cluster_bootstrap(paired)
        four.append(record); interactions.append({"task_key":task,"interaction_I_task":interaction,"paired_seed_values":";".join(map(str,paired)),"paired_bootstrap95_low":low,"paired_bootstrap95_high":high})
    write_csv(a.output_dir/"stage4_analysis_four_cell_by_task.csv",four); write_csv(a.output_dir/"stage4_analysis_interaction_by_task.csv",interactions)
    diagnostics=[]
    for task in TASKS:
        for scene in ("id","ood"):
            for delay in (0,200):
                cell=[r for r in rows if r["task_key"]==task and r["scene_condition"]==scene and int(r["added_delay_ms"])==delay]
                diagnostics.append({"task_key":task,"scene_condition":scene,"added_delay_ms":delay,"episodes":len(cell),"mean_request_latency_ms":sum(float(r["measured_request_latency_ms"]) for r in cell)/len(cell),"mean_logical_delay_steps":sum(float(r["logical_delay_steps"]) for r in cell)/len(cell),"mean_action_age_ms":sum(float(r["mean_action_age_ms"]) for r in cell)/len(cell),"mean_queue_underrun_steps":sum(int(r["queue_underrun_steps"]) for r in cell)/len(cell),"mean_hold_action_fraction":sum(float(r["hold_action_fraction"]) for r in cell)/len(cell)})
    write_csv(a.output_dir/"stage4_timing_diagnostics.csv",diagnostics)
    lines=["# Stage 4 Observations","","OpenVLA-OFT second-policy diagnostic; naive asynchronous execution, not RTC.",""]
    for row in interactions:
        cell=next(x for x in four if x["task_key"]==row["task_key"])
        lines.append(f"- {row['task_key']}: ID Native {cell['id_native_successes']}/8, ID +200 {cell['id_plus_200_successes']}/8, OOD Native {cell['ood_native_successes']}/8, OOD +200 {cell['ood_plus_200_successes']}/8; I={float(row['interaction_I_task']):+.3f}, paired bootstrap 95% CI [{float(row['paired_bootstrap95_low']):+.3f}, {float(row['paired_bootstrap95_high']):+.3f}].")
    lines.extend(["","Interpret qualitatively against the frozen pi0.5 references only; this is not an architecture-controlled comparison."])
    (a.output_dir/"STAGE_4_OBSERVATIONS.md").write_text("\n".join(lines)+"\n")
    os.environ["MPLBACKEND"]="Agg"; import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,4)); ax.bar([r["task_key"] for r in interactions],[float(r["interaction_I_task"]) for r in interactions]); ax.axhline(0,color="black",linewidth=1); ax.set(ylabel="OOD x delay interaction",title="Stage 4: OpenVLA-OFT second-policy diagnostic"); fig.tight_layout(); fig.savefig(a.output_dir/"stage4_interaction_by_task.png",dpi=180); plt.close(fig)
    print("PASS: complete Stage 4 second-policy analysis generated"); return 0


if __name__=="__main__": raise SystemExit(main())
