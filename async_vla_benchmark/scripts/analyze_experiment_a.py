#!/usr/bin/env python3
import argparse,hashlib,json,os
from pathlib import Path
from async_vla_benchmark.benchmark.experiment_a import HORIZON,SEEDS,validate_frozen_variants
from async_vla_benchmark.benchmark.logging import read_csv,write_csv
from async_vla_benchmark.scripts.analyze_stage3 import paired_cluster_bootstrap,wilson

def main():
 p=argparse.ArgumentParser(); p.add_argument("--results",type=Path,required=True); p.add_argument("--variants",type=Path,required=True); p.add_argument("--validation",type=Path,required=True); p.add_argument("--stage3-results",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
 validation=json.loads(a.validation.read_text())
 if validation.get("status")!="pass": raise ValueError("Experiment A analysis requires a complete passing validation record")
 rows=read_csv(a.results); variants=read_csv(a.variants); validate_frozen_variants(variants)
 if len(rows)!=64 or len({r["run_id"] for r in rows})!=64 or any(not r.get("status","").startswith("ok") for r in rows): raise ValueError("Experiment A analysis requires 64 unique valid rows")
 a.output_dir.mkdir(parents=True,exist_ok=True); four=[]; interactions=[]
 def outcome(scene,variant_name,delay,seed):
  matches=[r for r in rows if r["scene_condition"]==scene and r["variant_name"]==variant_name and int(r["added_delay_ms"])==delay and int(r["seed"])==seed]
  if len(matches)!=1: raise ValueError(f"expected one {scene}/{variant_name}/{delay}/s{seed} row, got {len(matches)}")
  return int(matches[0]["success"])
 for variant in variants:
  name=variant["variant_name"]; rec={"classification_id":variant["classification_id"],"api_task_index":variant["api_task_index"],"difficulty_level":variant["difficulty_level"],"variant_name":name,"analysis_status":"targeted_post_stage3b_variant_generalization","configured_n_action_steps":HORIZON}
  for scene in ("id","ood"):
   target="KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it" if scene=="id" else name
   for delay,label in ((0,"native"),(200,"plus_200")):
    cell=[r for r in rows if r["scene_condition"]==scene and r["variant_name"]==target and int(r["added_delay_ms"])==delay]; k=sum(int(r["success"]) for r in cell); lo,hi=wilson(k,len(cell)); prefix=f"{scene}_{label}"; rec.update({prefix+"_successes":k,prefix+"_trials":len(cell),prefix+"_rate":k/len(cell),prefix+"_wilson95_low":lo,prefix+"_wilson95_high":hi})
  paired=[]
  for seed in SEEDS: paired.append((outcome("ood",name,200,seed)-outcome("ood",name,0,seed))-(outcome("id","KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",200,seed)-outcome("id","KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",0,seed)))
  interaction=(rec["ood_plus_200_rate"]-rec["ood_native_rate"])-(rec["id_plus_200_rate"]-rec["id_native_rate"]); lo,hi=paired_cluster_bootstrap(paired); four.append(rec); interactions.append({"classification_id":variant["classification_id"],"variant_name":name,"difficulty_level":variant["difficulty_level"],"interaction_I_variant":interaction,"paired_seed_values":";".join(map(str,paired)),"paired_bootstrap95_low":lo,"paired_bootstrap95_high":hi})
 write_csv(a.output_dir/"experiment_a_four_cell_by_variant.csv",four); write_csv(a.output_dir/"experiment_a_interaction_by_variant.csv",interactions)
 negative=sum(float(r["interaction_I_variant"])<0 for r in interactions); mean_i=sum(float(r["interaction_I_variant"]) for r in interactions)/3; gate_pass=negative>=2 and mean_i<0
 stage3=read_csv(a.stage3_results); prior=[r for r in stage3 if r["task_key"]=="long_stove_moka" and r["perturbation_key"]=="object_layout" and int(r["configured_n_action_steps"])==25]
 prior_cells=[]
 for scene in ("id","ood"):
  for delay in (0,200):
   cell=[r for r in prior if r["scene_condition"]==scene and int(r["added_delay_ms"])==delay]; prior_cells.append({"source":"stage3_separate_seed_block","variant_name":"KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25","scene_condition":scene,"added_delay_ms":delay,"successes":sum(int(r["success"]) for r in cell),"trials":len(cell)})
 write_csv(a.output_dir/"experiment_a_prior_add25_separate.csv",prior_cells)
 gate={"gate_version":"experiment_a_to_b_v1","negative_variants":negative,"total_variants":3,"mean_interaction":mean_i,"experiment_b_dispatch":gate_pass,"validation_status":"pass","validation_sha256":hashlib.sha256(a.validation.read_bytes()).hexdigest(),"experiment_a_results_sha256":hashlib.sha256(a.results.read_bytes()).hexdigest(),"frozen_variants_sha256":hashlib.sha256(a.variants.read_bytes()).hexdigest()}; (a.output_dir/"experiment_a_to_b_gate.json").write_text(json.dumps(gate,indent=2)+"\n")
 os.environ["MPLBACKEND"]="Agg"; import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(7,4)); labels=[f"c{r['classification_id']}" for r in interactions]; values=[float(r["interaction_I_variant"]) for r in interactions]; ax.bar(labels,values); ax.axhline(0,color="black",linewidth=1); ax.set(ylabel="OOD × delay interaction",title="Experiment A: new stove/moka layout variants"); fig.tight_layout(); fig.savefig(a.output_dir/"experiment_a_interaction_by_variant.png",dpi=180); plt.close(fig)
 lines=["# Experiment A Observations","",f"- Negative interactions: {negative}/3.",f"- Mean interaction: {mean_i:+.3f}.",f"- Frozen Experiment B gate: {'PASS' if gate_pass else 'FAIL'}.","","The completed Stage-3 _add_25 seed block is reported separately and is not pooled with Experiment A."]
 for r in interactions: lines.append(f"- c{r['classification_id']}: I={float(r['interaction_I_variant']):+.3f}, paired bootstrap 95% CI [{float(r['paired_bootstrap95_low']):+.3f}, {float(r['paired_bootstrap95_high']):+.3f}].")
 (a.output_dir/"EXPERIMENT_A_OBSERVATIONS.md").write_text("\n".join(lines)+"\n"); print("PASS: complete Experiment A analysis and frozen Experiment B gate generated"); return 0
if __name__=="__main__": raise SystemExit(main())
