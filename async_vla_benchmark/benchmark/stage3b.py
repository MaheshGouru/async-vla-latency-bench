"""Frozen targeted Stage 3B object-layout cross-task replication."""
from __future__ import annotations
from dataclasses import asdict
from typing import Mapping, Sequence
from async_vla_benchmark.benchmark.stage3 import Stage3Plan

HORIZONS=(20,25,30); ADDED_DELAYS_MS=(0,200); SEEDS=tuple(range(14,22))
ANALYSIS_STATUS="targeted_post_stage3"
TASKS={
 "spatial_transport":{"suite":"libero_spatial","task_id":2,"base_name":"pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate","task_group":"single_stage_transport"},
 "goal_drawer":{"suite":"libero_goal","task_id":0,"base_name":"open_the_middle_drawer_of_the_cabinet","task_group":"articulated_contact_rich"},
}
VARIANTS={
 "spatial_transport":{"classification_id":1773,"api_task_index":1772,"difficulty_level":3,"variant_name":"pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15"},
 "goal_drawer":{"classification_id":1891,"api_task_index":1890,"difficulty_level":2,"variant_name":"open_the_middle_drawer_of_the_cabinet_add_13"},
}

def _row(provenance,task_key,scene,horizon,delay,seed):
 task=TASKS[task_key]; variant=VARIANTS.get(task_key) if scene=="ood" else None
 api=variant["api_task_index"] if variant else task["task_id"]; name=variant["variant_name"] if variant else task["base_name"]
 perturbation="object_layout" if variant else "id"
 run_id=f"stage3b__{task_key}__{scene}__{perturbation}__rtc__h{horizon}__d{delay}__s{seed}"
 return Stage3Plan(run_id=run_id,stage="stage3b",analysis_status=ANALYSIS_STATUS,
  git_sha=provenance["git_sha"],lerobot_git_sha=provenance["lerobot_git_sha"],libero_plus_git_sha=provenance["libero_plus_git_sha"],model_revision=provenance["model_revision"],
  checkpoint_id="lerobot/pi05_libero_finetuned@"+provenance["model_revision"],runner_commit=provenance["git_sha"],environment_version=provenance["libero_plus_git_sha"] if scene=="ood" else provenance["lerobot_git_sha"],
  task_key=task_key,task_group=task["task_group"],suite=task["suite"],base_task_id=task["task_id"],base_task_name=task["base_name"],task_id=api,task_name=name,api_task_index=api,variant_name=name,
  classification_id=str(variant["classification_id"]) if variant else "",difficulty_level=str(variant["difficulty_level"]) if variant else "",perturbation_key=perturbation,official_category="Objects Layout" if variant else "ID",mechanism_group="trajectory_adaptation" if variant else "id",
  scene=scene,scene_condition=scene,execution_method="rtc",configured_n_action_steps=horizon,rtc_execution_horizon=horizon,request_threshold_actions=horizon,added_delay_ms=delay,delay_condition="native" if delay==0 else "plus_200ms",seed=seed,
  initialization_index_or_id="libero_episode_index:0",initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",output_path=f"episodes/{run_id}.json")

def stage3b_manifest(provenance:Mapping[str,str]):
 rows=[]
 for task,scenes in (("spatial_transport",("id","ood")),("goal_drawer",("ood",))):
  for scene in scenes:
   for h in HORIZONS:
    for d in ADDED_DELAYS_MS:
     for seed in SEEDS: rows.append(_row(provenance,task,scene,h,d,seed))
 validate_manifest(rows); return rows

def validate_manifest(rows:Sequence[Stage3Plan]):
 if len(rows)!=144 or len({r.run_id for r in rows})!=144: raise ValueError("Stage 3B must contain 144 unique new episodes")
 if sum(r.scene=="ood" for r in rows)!=96 or sum(r.scene=="id" for r in rows)!=48: raise ValueError("Stage 3B new accounting must be 96 OOD + 48 ID")
 if any(r.task_key=="goal_drawer" and r.scene=="id" for r in rows): raise ValueError("goal ID must be reused, not rerun")
 if any(r.task_key=="long_stove_moka" for r in rows): raise ValueError("long task must not be rerun")
 if {r.configured_n_action_steps for r in rows}!=set(HORIZONS) or {r.added_delay_ms for r in rows}!=set(ADDED_DELAYS_MS) or {r.seed for r in rows}!=set(SEEDS): raise ValueError("wrong Stage 3B matrix")
 actual={(r.task_key,r.classification_id,r.api_task_index,r.variant_name,r.difficulty_level) for r in rows if r.scene=="ood"}
 expected={(k,str(v["classification_id"]),v["api_task_index"],v["variant_name"],str(v["difficulty_level"])) for k,v in VARIANTS.items()}
 if actual!=expected: raise ValueError("frozen Stage 3B variant identity changed")

def as_rows(rows): return [asdict(r) for r in rows]
