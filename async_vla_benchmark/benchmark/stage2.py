"""Frozen Stage 2 local operating-point sensitivity design."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .stage0 import STAGE0_TASKS

HORIZONS = (10, 15, 20, 25, 30, 35)
ADDED_DELAYS_MS = (0, 100, 200, 300)
SEEDS = (5, 6, 7, 8, 9)
METHOD = "rtc"


@dataclass(frozen=True)
class Stage2Plan:
    run_id: str
    stage: str
    analysis_status: str
    git_sha: str
    lerobot_git_sha: str
    model_revision: str
    checkpoint_id: str
    runner_commit: str
    environment_version: str
    task_key: str
    task_group: str
    suite: str
    base_task_id: int
    base_task_name: str
    task_id: int
    task_name: str
    api_task_index: int
    variant_name: str
    classification_id: str
    difficulty_level: str
    perturbation_key: str
    scene: str
    scene_condition: str
    execution_method: str
    configured_n_action_steps: int
    rtc_execution_horizon: int
    request_threshold_actions: int
    added_delay_ms: int
    delay_condition: str
    seed: int
    initialization_index_or_id: str
    initial_state_fingerprint: str
    initial_state_fingerprint_method: str
    output_path: str
    status: str = "pending"
    invalid_reason: str = ""


def stage2_manifest(provenance: Mapping[str, str]) -> list[Stage2Plan]:
    rows: list[Stage2Plan] = []
    for task in STAGE0_TASKS:
        for horizon in HORIZONS:
            for delay in ADDED_DELAYS_MS:
                for seed in SEEDS:
                    run_id = f"stage2__{task.task_key}__rtc__h{horizon}__d{delay}__s{seed}"
                    rows.append(Stage2Plan(
                        run_id=run_id,
                        stage="stage2",
                        analysis_status="posthoc_sensitivity",
                        git_sha=provenance["git_sha"],
                        lerobot_git_sha=provenance["lerobot_git_sha"],
                        model_revision=provenance["model_revision"],
                        checkpoint_id="lerobot/pi05_libero_finetuned@" + provenance["model_revision"],
                        runner_commit=provenance["git_sha"],
                        environment_version=provenance["lerobot_git_sha"],
                        task_key=task.task_key,
                        task_group=task.task_group,
                        suite=task.suite,
                        base_task_id=task.task_id,
                        base_task_name=task.expected_task_name,
                        task_id=task.task_id,
                        task_name=task.expected_task_name,
                        api_task_index=task.task_id,
                        variant_name=task.expected_task_name,
                        classification_id="",
                        difficulty_level="",
                        perturbation_key="id",
                        scene="id",
                        scene_condition="id",
                        execution_method=METHOD,
                        configured_n_action_steps=horizon,
                        rtc_execution_horizon=horizon,
                        request_threshold_actions=horizon,
                        added_delay_ms=delay,
                        delay_condition="native" if delay == 0 else f"plus_{delay}ms",
                        seed=seed,
                        initialization_index_or_id="libero_episode_index:0",
                        initial_state_fingerprint="PENDING_PREFLIGHT_RESOLUTION",
                        initial_state_fingerprint_method="PENDING_PREFLIGHT_RESOLUTION",
                        output_path=f"episodes/{run_id}.json",
                    ))
    validate_manifest(rows)
    return rows


def validate_manifest(rows: Sequence[Stage2Plan]) -> None:
    if len(rows) != 360 or len({row.run_id for row in rows}) != 360:
        raise ValueError("Stage 2 manifest must contain 360 unique episodes")
    if {row.configured_n_action_steps for row in rows} != set(HORIZONS):
        raise ValueError("wrong Stage 2 horizon set")
    if {row.added_delay_ms for row in rows} != set(ADDED_DELAYS_MS):
        raise ValueError("wrong Stage 2 delay set")
    if {row.seed for row in rows} != set(SEEDS):
        raise ValueError("wrong Stage 2 seed set")
    if any(row.execution_method != METHOD or row.scene_condition != "id" for row in rows):
        raise ValueError("Stage 2 is RTC-only and ID-only")
    if any(row.rtc_execution_horizon != row.configured_n_action_steps for row in rows):
        raise ValueError("RTC execution horizon must follow configured action coverage")
    if any(row.request_threshold_actions != row.configured_n_action_steps for row in rows):
        raise ValueError("Stage 2 requests immediately when a response lands")


def as_rows(rows: Sequence[Stage2Plan]) -> list[dict]:
    return [asdict(row) for row in rows]
