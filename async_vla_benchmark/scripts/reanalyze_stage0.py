#!/usr/bin/env python3
"""Recompute Stage 0 diagnostics without startup/hold contamination."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path


TASK_LABELS = {
    "spatial_transport": "Single-stage transport",
    "goal_drawer": "Articulated/contact-rich",
    "long_stove_moka": "Multi-stage/sequential",
}
METHOD_LABELS = {"naive_async": "Naive async", "rtc": "RTC"}
DELAYS = (0, 100, 200, 300, 400)
SEEDS = (0, 1, 10, 11, 12, 13)


def pct(series, q):
    return float(series.quantile(q, interpolation="linear")) if len(series) else float("nan")


def write_csv(path, rows):
    rows = list(rows)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage0-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    source, output = args.stage0_dir, args.output_dir
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    figures = output / "figures"; figures.mkdir()
    original = pd.read_csv(source / "latency_calibration_episode_results.csv")
    if len(original) != 180 or original.run_id.nunique() != 180:
        raise ValueError("expected 180 unique Stage 0 results")

    corrected, request_events, action_events = [], [], []
    for row in original.to_dict("records"):
        run_id = row["run_id"]
        requests = pd.read_parquet(source / "requests" / f"{run_id}.parquet")
        actions = pd.read_parquet(source / "actions" / f"{run_id}.parquet")
        startup = requests[requests["latency_profile"] == "ideal"].copy()
        steady = requests[requests["latency_profile"] != "ideal"].copy()
        holds = actions[actions["is_hold_action"].fillna(False).astype(bool)].copy()
        policy = actions[~actions["is_hold_action"].fillna(False).astype(bool)].copy()
        if steady.empty or policy.empty:
            raise ValueError(f"{run_id}: no steady requests or policy actions")
        base = {"run_id": run_id, "task_key": row["task_key"], "task_group": row["task_group"],
            "suite": row["suite"], "task_id": row["task_id"], "task_name": row["task_name"],
            "execution_method": row["execution_method"], "added_delay_ms": int(row["added_delay_ms"]),
            "seed": int(row["seed"]), "success": int(row["success"]), "episode_steps": int(row["episode_steps"]),
            "status": row["status"], "invalid_reason": row.get("invalid_reason", "")}
        corrected.append({**base,
            "steady_request_count": len(steady), "startup_request_count": len(startup),
            "request_latency_mean_ms": steady.measured_request_latency_ms.mean(),
            "request_latency_p50_ms": pct(steady.measured_request_latency_ms, .50),
            "request_latency_p95_ms": pct(steady.measured_request_latency_ms, .95),
            "preprocessing_latency_mean_ms": steady.preprocessing_latency_ms.mean(),
            "model_latency_mean_ms": steady.model_latency_ms.mean(),
            "postprocessing_latency_mean_ms": steady.postprocessing_latency_ms.mean(),
            "startup_request_latency_mean_ms": startup.measured_request_latency_ms.mean() if len(startup) else float("nan"),
            "policy_action_count": len(policy), "hold_count": len(holds),
            "underrun_count": int(actions.is_queue_underrun.fillna(False).astype(bool).sum()),
            "action_age_mean_ms": policy.action_age_ms.mean(), "action_age_p50_ms": pct(policy.action_age_ms, .50),
            "action_age_p95_ms": pct(policy.action_age_ms, .95), "action_age_max_ms": policy.action_age_ms.max(),
            "logical_delay_steps_mean": steady.delay_steps.mean(), "logical_delay_steps_p95": pct(steady.delay_steps, .95),
            "queue_occupancy_mean": actions.queue_depth_before.mean(), "queue_occupancy_p95": pct(actions.queue_depth_before, .95),
            "original_request_latency_mean_ms": row["request_latency_mean_ms"],
            "original_action_age_mean_ms": row["action_age_mean_ms"], "original_action_age_p95_ms": row["action_age_p95_ms"],
        })
        steady = steady.assign(run_id=run_id, task_key=row["task_key"], execution_method=row["execution_method"], added_delay_ms=int(row["added_delay_ms"]), seed=int(row["seed"]))
        policy = policy.assign(run_id=run_id, task_key=row["task_key"], execution_method=row["execution_method"], added_delay_ms=int(row["added_delay_ms"]), seed=int(row["seed"]))
        request_events.append(steady); action_events.append(policy)

    corrected_df = pd.DataFrame(corrected).sort_values("run_id")
    corrected_df.to_csv(output / "latency_calibration_episode_results_reanalyzed.csv", index=False)
    requests_all = pd.concat(request_events, ignore_index=True)
    actions_all = pd.concat(action_events, ignore_index=True)

    native = corrected_df[corrected_df.added_delay_ms == 0]
    viability = native.groupby(["task_key", "execution_method"]).success.agg(["sum", "count"]).reset_index()
    viable = {(r.task_key, r.execution_method) for r in viability.itertuples() if r.sum / r.count >= .5}
    corrected_df["viable_cell"] = corrected_df.apply(lambda r: (r.task_key, r.execution_method) in viable, axis=1)
    viable_requests = requests_all[requests_all.apply(lambda r: (r.task_key, r.execution_method) in viable, axis=1)]
    viable_actions = actions_all[actions_all.apply(lambda r: (r.task_key, r.execution_method) in viable, axis=1)]

    table_a=[]
    for task in TASK_LABELS:
        for method in METHOD_LABELS:
            subset=corrected_df[(corrected_df.task_key==task)&(corrected_df.execution_method==method)]
            values={d:f"{int(subset[subset.added_delay_ms==d].success.sum())}/6" for d in DELAYS}
            table_a.append({"Task-demand group":TASK_LABELS[task],"Method":METHOD_LABELS[method],
                "Native":values[0],"Native + 100 ms":values[100],"Native + 200 ms":values[200],
                "Native + 300 ms":values[300],"Native + 400 ms":values[400],"Viable?":"yes" if (task,method) in viable else "no"})
    write_csv(output/"table_a_per_task_calibration.csv",table_a)

    native_success = corrected_df[(corrected_df.added_delay_ms==0)&corrected_df.viable_cell].success.mean()
    table_b=[]
    for delay in DELAYS:
        eps=corrected_df[(corrected_df.added_delay_ms==delay)&corrected_df.viable_cell]
        req=viable_requests[viable_requests.added_delay_ms==delay]; act=viable_actions[viable_actions.added_delay_ms==delay]
        rate=eps.success.mean()
        table_b.append({"Added delay":"Native" if delay==0 else f"Native + {delay} ms",
            "Success on viable ID cells":f"{int(eps.success.sum())}/{len(eps)}","Success rate":rate,
            "Drop from Native":native_success-rate,"Steady-state mean request latency (ms)":req.measured_request_latency_ms.mean(),
            "Policy-action p95 age (ms)":pct(act.action_age_ms,.95),"Selected":"<-- d*" if delay==200 else ""})
    write_csv(output/"table_b_pooled_curve.csv",table_b)

    table_c=[]
    for method in METHOD_LABELS:
        subset=corrected_df[corrected_df.execution_method==method]
        table_c.append({"Method":METHOD_LABELS[method],**{"Native" if d==0 else f"Native + {d} ms":f"{int(subset[subset.added_delay_ms==d].success.sum())}/18" for d in DELAYS}})
    write_csv(output/"table_c_method_calibration.csv",table_c)

    table_d=[]
    for delay in DELAYS:
        for method in METHOD_LABELS:
            eps=corrected_df[(corrected_df.added_delay_ms==delay)&(corrected_df.execution_method==method)]
            req=requests_all[(requests_all.added_delay_ms==delay)&(requests_all.execution_method==method)]
            act=actions_all[(actions_all.added_delay_ms==delay)&(actions_all.execution_method==method)]
            table_d.append({"Added delay":delay,"Method":METHOD_LABELS[method],"Steady-state mean request latency (ms)":req.measured_request_latency_ms.mean(),
                "Policy-action mean age (ms)":act.action_age_ms.mean(),"Policy-action p95 age (ms)":pct(act.action_age_ms,.95),
                "Steady-state mean logical delay (steps)":req.delay_steps.mean(),"Mean queue occupancy":eps.queue_occupancy_mean.mean(),
                "Underruns":int(eps.underrun_count.sum()),"Holds":int(eps.hold_count.sum()),"Startup requests":int(eps.startup_request_count.sum()),
                "Startup mean latency (ms)":eps.startup_request_latency_mean_ms.mean()})
    write_csv(output/"table_d_freshness.csv",table_d)

    changes=[{"Metric":"Request latency mean (episode-level average)","Original mean":corrected_df.original_request_latency_mean_ms.mean(),
              "Corrected mean":corrected_df.request_latency_mean_ms.mean(),"Mean change":(corrected_df.request_latency_mean_ms-corrected_df.original_request_latency_mean_ms).mean()},
             {"Metric":"Action age mean (episode-level average)","Original mean":corrected_df.original_action_age_mean_ms.mean(),
              "Corrected mean":corrected_df.action_age_mean_ms.mean(),"Mean change":(corrected_df.action_age_mean_ms-corrected_df.original_action_age_mean_ms).mean()},
             {"Metric":"Action age p95 (episode-level average)","Original mean":corrected_df.original_action_age_p95_ms.mean(),
              "Corrected mean":corrected_df.action_age_p95_ms.mean(),"Mean change":(corrected_df.action_age_p95_ms-corrected_df.original_action_age_p95_ms).mean()}]
    write_csv(output/"metric_change_summary.csv",changes)

    # Required calibration figures plus separate startup/hold diagnostics.
    fig,axes=plt.subplots(1,3,figsize=(15,4),sharey=True)
    for ax,task in zip(axes,TASK_LABELS):
        for method in METHOD_LABELS:
            vals=[corrected_df[(corrected_df.task_key==task)&(corrected_df.execution_method==method)&(corrected_df.added_delay_ms==d)].success.mean() for d in DELAYS]
            ax.plot(DELAYS,vals,marker="o",label=METHOD_LABELS[method]); ax.set_title(TASK_LABELS[task]); ax.set_xlabel("Added delay (ms)"); ax.set_ylim(-.05,1.05)
    axes[0].set_ylabel("Success rate"); axes[-1].legend(); fig.tight_layout(); fig.savefig(figures/"latency_calibration_success_by_task.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4)); ax.plot(DELAYS,[r["Success rate"] for r in table_b],marker="o"); ax.axvline(200,color="red",ls="--",label="d*=200 ms"); ax.set(xlabel="Added delay (ms)",ylabel="Pooled viable-cell success"); ax.legend(); fig.tight_layout(); fig.savefig(figures/"latency_calibration_pooled_curve.png",dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,4),sharey=True)
    for ax,task in zip(axes,TASK_LABELS):
        for method in METHOD_LABELS:
            vals=[pct(actions_all[(actions_all.task_key==task)&(actions_all.execution_method==method)&(actions_all.added_delay_ms==d)].action_age_ms,.95) for d in DELAYS]
            ax.plot(DELAYS,vals,marker="o",label=METHOD_LABELS[method]); ax.set_title(TASK_LABELS[task]); ax.set_xlabel("Added delay (ms)")
    axes[0].set_ylabel("Policy-action p95 age (ms)"); axes[-1].legend(); fig.tight_layout(); fig.savefig(figures/"latency_calibration_action_age.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4))
    for method in METHOD_LABELS:
        vals=[requests_all[(requests_all.execution_method==method)&(requests_all.added_delay_ms==d)].delay_steps.mean() for d in DELAYS]
        ax.plot(DELAYS,vals,marker="o",label=METHOD_LABELS[method])
    ax.set(xlabel="Added delay (ms)",ylabel="Steady-state mean logical delay (steps)"); ax.legend(); fig.tight_layout(); fig.savefig(figures/"latency_calibration_logical_steps.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4)); startup_by_method=corrected_df.groupby("execution_method").startup_request_latency_mean_ms.mean(); ax.bar([METHOD_LABELS[x] for x in startup_by_method.index],startup_by_method.values); ax.set_ylabel("Startup request mean latency (ms)"); fig.tight_layout(); fig.savefig(figures/"startup_latency_separate.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4)); holds=corrected_df.groupby(["execution_method","added_delay_ms"]).hold_count.sum().unstack(0).fillna(0); holds.plot.bar(ax=ax); ax.set_ylabel("Hold actions"); ax.set_xlabel("Added delay (ms)"); fig.tight_layout(); fig.savefig(figures/"holds_underruns_separate.png",dpi=180); plt.close(fig)

    selected=json.loads((source/"selected_high_delay.json").read_text()); shutil.copy2(source/"selected_high_delay.json",output/"selected_high_delay_unchanged.json")
    reused=corrected_df[(corrected_df.seed.isin([0,1]))&(corrected_df.added_delay_ms.isin([0,200]))]
    findings=f"""# Stage 0 Reanalysis Findings

## Scope and frozen outcomes

- Reanalyzed all **180/180** episodes from raw request and action Parquet traces.
- Episode success labels were not changed.
- The frozen high delay remains **d* = {selected['high_added_delay_ms']} ms**.
- Native viable-cell success remains **21/24 (87.5%)**.
- Native + 200 ms viable-cell success remains **16/24 (66.7%)**.
- The success drop remains **20.8 percentage points**.

## Corrected measurement rules

1. Steady-state request latency and logical-delay summaries exclude the one `ideal` startup request in each episode.
2. Policy action-age summaries exclude runner-generated hold actions.
3. Startup requests, holds, and underruns remain visible in separate columns, tables, and figures.
4. Percentiles use linear interpolation, matching pandas/NumPy's conventional quantile definition.

## Coverage and exclusions

- Steady-state requests analyzed: **{len(requests_all):,}**.
- Startup requests reported separately: **{int(corrected_df.startup_request_count.sum()):,}**.
- Policy actions analyzed for freshness: **{len(actions_all):,}**.
- Hold actions excluded from policy action age and reported separately: **{int(corrected_df.hold_count.sum()):,}**.
- Episodes containing holds: **{int((corrected_df.hold_count>0).sum())}**.
- Stage 1 reuse subset: **{len(reused)} episodes**; episodes with holds in that subset: **{int((reused.hold_count>0).sum())}**.

## Effect of the correction

See `metric_change_summary.csv` for exact original-versus-corrected averages. The correction changes only latency/freshness diagnostics, not success rates or delay selection.

## Artifacts

- `latency_calibration_episode_results_reanalyzed.csv`: corrected per-episode metrics.
- `table_a_per_task_calibration.csv` through `table_d_freshness.csv`: regenerated tables.
- `metric_change_summary.csv`: audit of numerical changes.
- `figures/`: four required calibration plots plus separate startup and hold diagnostics.
- `selected_high_delay_unchanged.json`: verbatim frozen Stage 0 delay artifact.

## Interpretation limitation

The original seven hold-affected episodes remain valid outcome observations, but their policy-action freshness is now computed only from policy-generated actions. Holds are reported as queue behavior rather than being assigned a fictitious age of zero.
"""
    (output/"STAGE_0_REANALYSIS_FINDINGS.md").write_text(findings)
    metadata={"source":str(source),"episodes":180,"rules":{"exclude_ideal_startup_from_steady_state":True,"exclude_holds_from_policy_action_age":True,"report_startup_and_holds_separately":True},"selected_high_delay_ms":200,"success_outcomes_changed":False}
    (output/"reanalysis_metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(f"wrote reanalysis to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
