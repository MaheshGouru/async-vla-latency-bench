#!/usr/bin/env python3
import argparse, math, os, random
from pathlib import Path
from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage3 import HORIZONS, OOD_VARIANTS, POSTHOC, PRESPECIFIED, SEEDS


def rate(rows): return sum(int(r["success"]) for r in rows)/len(rows) if rows else float("nan")
def wilson(k,n,z=1.959963984540054):
    if not n:return float("nan"),float("nan")
    p=k/n; den=1+z*z/n; center=(p+z*z/(2*n))/den; margin=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den; return center-margin,center+margin
def paired_cluster_bootstrap(values, draws=10000):
    """Resample held-out seed clusters; each value already carries all four cells."""
    rng=random.Random(20260816); means=[]; n=len(values)
    for _ in range(draws): means.append(sum(values[rng.randrange(n)] for _ in range(n))/n)
    means.sort()
    def q(p):
        x=(len(means)-1)*p; lo=math.floor(x); hi=math.ceil(x); return means[lo] if lo==hi else means[lo]*(hi-x)+means[hi]*(x-lo)
    return q(.025),q(.975)


def paired_interaction_values(rows, task, perturbation, horizon, seeds=SEEDS):
    """Return one four-cell difference-in-differences value per held-out seed."""
    def outcome(scene, delay, seed):
        matches = [r for r in rows if r["task_key"] == task
                   and r["scene_condition"] == scene
                   and int(r["configured_n_action_steps"]) == horizon
                   and int(r["added_delay_ms"]) == delay
                   and int(r["seed"]) == seed
                   and (scene == "id" or r["perturbation_key"] == perturbation)]
        if len(matches) != 1:
            raise ValueError(f"expected one cell for {task}/{perturbation}/h{horizon}/s{seed}/{scene}/{delay}; got {len(matches)}")
        return int(matches[0]["success"])
    return [(outcome("ood", 200, seed) - outcome("ood", 0, seed))
            - (outcome("id", 200, seed) - outcome("id", 0, seed))
            for seed in seeds]


def main():
    p=argparse.ArgumentParser(); p.add_argument("--results",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--allow-incomplete",action="store_true"); args=p.parse_args()
    rows=[r for r in read_csv(args.results) if r.get("status","").startswith("ok")]
    if len(rows)!=288 and not args.allow_incomplete: raise ValueError(f"refusing incomplete analysis: {len(rows)}/288")
    if not args.allow_incomplete:
        unique={r["run_id"]:r for r in rows}
        if len(unique)!=288: raise ValueError("duplicate result run_ids would bias Stage 3 analysis")
        primary=[r for r in unique.values() if r["analysis_status"]==PRESPECIFIED]
        posthoc=[r for r in unique.values() if r["analysis_status"]==POSTHOC]
        if len(primary)!=240 or len(posthoc)!=48: raise ValueError("primary/post-hoc accounting must be 240/48")
    args.output_dir.mkdir(parents=True,exist_ok=True); four=[]; interactions=[]
    # This is the only pooled episode-accounting table. ID rows occur once here,
    # even though the same goal-drawer ID reference is reused in candidate-level contrasts.
    unique_primary=sorted((r for r in {r["run_id"]:r for r in rows}.values() if r["analysis_status"]==PRESPECIFIED),key=lambda r:r["run_id"])
    write_csv(args.output_dir/"stage3_primary_unique_episode_accounting.csv",unique_primary)
    for variant in OOD_VARIANTS:
        task=variant["task_key"]; perturbation=variant["perturbation_key"]
        for h in HORIZONS:
            cells={}
            for scene in ("id","ood"):
                for delay in (0,200):
                    cell=[r for r in rows if r["task_key"]==task and r["scene_condition"]==scene and int(r["configured_n_action_steps"])==h and int(r["added_delay_ms"])==delay and (scene=="id" or r["perturbation_key"]==perturbation)]
                    k=sum(int(r["success"]) for r in cell); lo,hi=wilson(k,len(cell)); cells[(scene,delay)]=(cell,k,lo,hi)
            record={"task_key":task,"perturbation_key":perturbation,"analysis_status":variant["analysis_status"],"configured_n_action_steps":h}
            for scene,label in (("id","id"),("ood","ood")):
                for delay,dlabel in ((0,"native"),(200,"plus_200")):
                    cell,k,lo,hi=cells[(scene,delay)]; record.update({f"{label}_{dlabel}_successes":k,f"{label}_{dlabel}_trials":len(cell),f"{label}_{dlabel}_rate":rate(cell),f"{label}_{dlabel}_wilson95_low":lo,f"{label}_{dlabel}_wilson95_high":hi})
            four.append(record)
            paired=paired_interaction_values(rows,task,perturbation,h)
            interaction=(record["ood_plus_200_rate"]-record["ood_native_rate"])-(record["id_plus_200_rate"]-record["id_native_rate"]); blo,bhi=paired_cluster_bootstrap(paired)
            interactions.append({"task_key":task,"perturbation_key":perturbation,"analysis_status":variant["analysis_status"],"configured_n_action_steps":h,"shared_id_reference":True,"interaction_I_h":interaction,"paired_seed_mean":sum(paired)/len(paired),"paired_seed_values":";".join(map(str,paired)),"paired_bootstrap95_low":blo,"paired_bootstrap95_high":bhi})
    write_csv(args.output_dir/"stage3_four_cell_by_horizon.csv",four); write_csv(args.output_dir/"stage3_interaction_by_horizon.csv",interactions)
    write_csv(args.output_dir/"stage3_posthoc_sensor_noise.csv",[r for r in four if r["analysis_status"]=="posthoc_replication"])
    os.environ["MPLBACKEND"]="Agg"; import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    labels={"object_layout":"Object layout","robot_initial_state":"Robot initial state","light_conditions":"Lighting","sensor_noise":"Sensor noise (post-hoc)"}
    fig,ax=plt.subplots(figsize=(7,5))
    for key in ("object_layout","robot_initial_state","light_conditions"):
        subset=[r for r in interactions if r["perturbation_key"]==key]; ax.plot(HORIZONS,[float(r["interaction_I_h"]) for r in subset],marker="o",label=labels[key])
    ax.axhline(0,color="black",linewidth=1); ax.axvline(25,color="black",linestyle="--",alpha=.4); ax.set(xlabel="Configured action coverage",ylabel="OOD × delay interaction I_h",title="Stage 3 prespecified held-out interactions"); ax.legend(); fig.tight_layout(); fig.savefig(args.output_dir/"stage3_prespecified_interaction_vs_horizon.png",dpi=180); plt.close(fig)
    filenames={"object_layout":"stage3_object_layout.png","robot_initial_state":"stage3_robot_initial_state.png","light_conditions":"stage3_lighting.png","sensor_noise":"stage3_sensor_noise_posthoc.png"}
    for key,filename in filenames.items():
        subset=[r for r in four if r["perturbation_key"]==key]; fig,axes=plt.subplots(1,3,figsize=(11,3.5),sharey=True)
        for ax,row,h in zip(axes,subset,HORIZONS):
            ax.plot([0,200],[float(row["id_native_rate"]),float(row["id_plus_200_rate"])],marker="o",label="ID"); ax.plot([0,200],[float(row["ood_native_rate"]),float(row["ood_plus_200_rate"])],marker="o",label="OOD"); ax.set_title(f"h={h}"); ax.set_xticks([0,200],["Native","+200"]); ax.set_ylim(-.05,1.05)
        axes[0].set_ylabel("Success rate"); axes[-1].legend(); fig.suptitle(labels[key]); fig.tight_layout(); fig.savefig(args.output_dir/filename,dpi=180); plt.close(fig)
    h25=[r for r in interactions if int(r["configured_n_action_steps"])==25]
    lines=["# Stage 3 OOD Confirmation Observations","",f"- Completed: {len(rows)}/288 episodes.","- Primary evidence: three prespecified task–perturbation candidates on held-out seeds.","- Sensor noise remains a separately labeled post-hoc replication.","","## h=25 confirmation gate",""]
    for r in h25: lines.append(f"- {r['task_key']} × {r['perturbation_key']} ({r['analysis_status']}): I_25={float(r['interaction_I_h']):+.3f}, paired bootstrap 95% CI [{float(r['paired_bootstrap95_low']):+.3f}, {float(r['paired_bootstrap95_high']):+.3f}].")
    lines += ["","## Guardrail","","Stage 2 is supporting sensitivity evidence only. It did not alter the frozen Stage 3 horizons, delays, seeds, or exact Stage 1 OOD variant identities."]
    (args.output_dir/"STAGE_3_OOD_CONFIRMATION_OBSERVATIONS.md").write_text("\n".join(lines)+"\n")
    print(f"PASS: complete Stage 3 analysis generated in {args.output_dir}"); return 0


if __name__=="__main__": raise SystemExit(main())
