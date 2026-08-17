#!/usr/bin/env python3
import argparse,os
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv,write_csv
from async_vla_benchmark.benchmark.stage3b import HORIZONS,SEEDS
from async_vla_benchmark.scripts.analyze_stage3 import paired_cluster_bootstrap,paired_interaction_values,wilson

TASKS=(("spatial_transport","object_layout","stage3b"),("goal_drawer","object_layout","stage3b"),("long_stove_moka","object_layout","stage3"))

def harmonize_columns(rows):
 """Return heterogeneous reused/new result rows with one stable union schema."""
 fields=[]
 for row in rows:
  for field in row:
   if field not in fields: fields.append(field)
 return [{field:row.get(field,"") for field in fields} for row in rows]

def main():
 p=argparse.ArgumentParser(); p.add_argument("--stage3b-results",type=Path,required=True); p.add_argument("--stage3-results",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
 new=read_csv(a.stage3b_results); old=read_csv(a.stage3_results)
 if len(new)!=144 or any(not r.get("status","").startswith("ok") for r in new): raise ValueError("Stage 3B results must be 144 complete valid rows")
 goal_id=[r for r in old if r["task_key"]=="goal_drawer" and r["scene_condition"]=="id"]
 long=[r for r in old if r["task_key"]=="long_stove_moka" and (r["scene_condition"]=="id" or r["perturbation_key"]=="object_layout")]
 two=new+goal_id; three=two+long
 if len(two)!=192 or len({r["run_id"] for r in two})!=192: raise ValueError("two-task analysis must contain 192 unique rows")
 if len(three)!=288 or len({r["run_id"] for r in three})!=288: raise ValueError("three-task synthesis must contain 288 unique rows")
 a.output_dir.mkdir(parents=True,exist_ok=True); write_csv(a.output_dir/"stage3b_object_layout_three_task_analysis.csv",harmonize_columns(three))
 four=[]; interactions=[]
 for task,perturbation,source in TASKS:
  for h in HORIZONS:
   rec={"task_key":task,"perturbation_key":perturbation,"analysis_status":"targeted_post_stage3" if source=="stage3b" else "prespecified_confirmatory_reused","configured_n_action_steps":h}
   for scene in ("id","ood"):
    for delay,label in ((0,"native"),(200,"plus_200")):
     cell=[r for r in three if r["task_key"]==task and r["scene_condition"]==scene and int(r["configured_n_action_steps"])==h and int(r["added_delay_ms"])==delay and (scene=="id" or r["perturbation_key"]==perturbation)]
     k=sum(int(r["success"]) for r in cell); lo,hi=wilson(k,len(cell)); prefix=f"{scene}_{label}"; rec.update({prefix+"_successes":k,prefix+"_trials":len(cell),prefix+"_rate":k/len(cell),prefix+"_wilson95_low":lo,prefix+"_wilson95_high":hi})
   four.append(rec); paired=paired_interaction_values(three,task,perturbation,h,seeds=SEEDS); lo,hi=paired_cluster_bootstrap(paired)
   interaction=(rec["ood_plus_200_rate"]-rec["ood_native_rate"])-(rec["id_plus_200_rate"]-rec["id_native_rate"])
   interactions.append({"task_key":task,"perturbation_key":perturbation,"analysis_status":rec["analysis_status"],"configured_n_action_steps":h,"interaction_I_h":interaction,"paired_seed_values":";".join(map(str,paired)),"paired_bootstrap95_low":lo,"paired_bootstrap95_high":hi})
 write_csv(a.output_dir/"stage3b_four_cell_by_task_horizon.csv",four); write_csv(a.output_dir/"stage3b_interaction_by_task_horizon.csv",interactions)
 os.environ["MPLBACKEND"]="Agg"; import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(7,5))
 for task in ("spatial_transport","goal_drawer","long_stove_moka"):
  sub=[r for r in interactions if r["task_key"]==task]; ax.plot(HORIZONS,[r["interaction_I_h"] for r in sub],marker="o",label=task)
 ax.axhline(0,color="black",linewidth=1); ax.set(xlabel="Configured action coverage",ylabel="OOD × delay interaction I_h",title="Stage 3B object-layout cross-task replication"); ax.legend(); fig.tight_layout(); fig.savefig(a.output_dir/"stage3b_object_layout_cross_task.png",dpi=180); plt.close(fig)
 lines=["# Stage 3B Object-Layout Observations","","Stage 3B is a targeted post-Stage-3 cross-task replication, not preregistered confirmation.",""]
 for r in interactions: lines.append(f"- {r['task_key']} h={r['configured_n_action_steps']}: I={r['interaction_I_h']:+.3f}, paired bootstrap 95% CI [{r['paired_bootstrap95_low']:+.3f}, {r['paired_bootstrap95_high']:+.3f}].")
 (a.output_dir/"STAGE_3B_OBJECT_LAYOUT_OBSERVATIONS.md").write_text("\n".join(lines)+"\n")
 print("PASS: complete Stage 3B two-task and three-task analysis generated"); return 0
if __name__=="__main__": raise SystemExit(main())
