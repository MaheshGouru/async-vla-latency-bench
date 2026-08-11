"""Frozen Stage 0 experiment matrix and delay-selection rules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .config import BenchmarkConfig, Stage0TaskConfig


EXPECTED_POLICY = "lerobot/pi05_libero_finetuned"
EXPECTED_METHODS = ("naive_async", "rtc")
EXPECTED_DELAYS_MS = (0, 100, 200, 300, 400, 500, 600, 700)
EXPECTED_SEEDS = (0, 1)
REFINEMENT_DELAYS_MS = (25, 50, 75)
REFINEMENT_SEEDS = (0, 1)
REFINEMENT_CELLS = (
    ("articulated_contact_rich", "naive_async"),
    ("articulated_contact_rich", "rtc"),
    ("multi_stage_sequential", "naive_async"),
)
REFINEMENT_STAGE = "stage0_refinement_25_75"
EXPECTED_TASKS = (
    (
        "single_stage_transport",
        "Single-stage transport",
        "libero_spatial",
        2,
        "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate",
    ),
    (
        "articulated_contact_rich",
        "Articulated/contact-rich",
        "libero_goal",
        0,
        "open_the_middle_drawer_of_the_cabinet",
    ),
    (
        "multi_stage_sequential",
        "Multi-stage/sequential",
        "libero_10",
        2,
        "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",
    ),
)


@dataclass(frozen=True)
class Stage0Plan:
    run_id: str
    task: Stage0TaskConfig
    execution_method: str
    added_delay_ms: int
    seed: int
    fixed_horizon: int
    stage: str = "stage0"
    episode_prefix: str = "stage0"

    @property
    def task_ref(self) -> str:
        return f"{self.task.suite}:{self.task.task_id}"

    @property
    def latency_profile(self) -> str:
        return "native" if self.added_delay_ms == 0 else f"native_plus_{self.added_delay_ms}"

    @property
    def episode_id(self) -> str:
        return (
            f"{self.episode_prefix}_{self.run_id}_{self.task.suite}_tid{self.task.task_id}_"
            f"{self.execution_method}_{self.latency_profile}_h{self.fixed_horizon}_s{self.seed}"
        )


def validate_stage0_config(cfg: BenchmarkConfig) -> None:
    """Fail before model loading if the frozen Stage 0 design has drifted."""
    if cfg.stage0 is None:
        raise ValueError("config has no stage0 section")
    if cfg.repository_revision is None:
        raise ValueError("Stage 0 requires a pinned LeRobot repository_revision")
    if cfg.checkpoint_revision is None:
        raise ValueError("Stage 0 requires a pinned checkpoint_revision")
    if cfg.policy_checkpoint != EXPECTED_POLICY:
        raise ValueError(f"Stage 0 policy must be {EXPECTED_POLICY}, got {cfg.policy_checkpoint}")
    if cfg.policy_n_action_steps != 10:
        raise ValueError("Stage 0 requires policy_n_action_steps=10")
    if cfg.max_parallel_tasks != 1:
        raise ValueError("Stage 0 requires max_parallel_tasks=1")
    if not cfg.rtc.enabled:
        raise ValueError("Stage 0 requires RTC to be enabled")

    stage0 = cfg.stage0
    if tuple(stage0.methods) != EXPECTED_METHODS:
        raise ValueError(f"Stage 0 methods must be {EXPECTED_METHODS}, got {stage0.methods}")
    if tuple(stage0.added_delays_ms) != EXPECTED_DELAYS_MS:
        raise ValueError(
            f"Stage 0 added delays must be {EXPECTED_DELAYS_MS}, got {stage0.added_delays_ms}"
        )
    if tuple(stage0.seeds) != EXPECTED_SEEDS:
        raise ValueError(f"Stage 0 seeds must be {EXPECTED_SEEDS}, got {stage0.seeds}")
    if stage0.fixed_horizon != 10:
        raise ValueError("Stage 0 requires fixed_horizon=10")

    tasks = tuple(
        (
            task.task_group_key,
            task.task_group_label,
            task.suite,
            task.task_id,
            task.task_name,
        )
        for task in stage0.tasks
    )
    if tasks != EXPECTED_TASKS:
        raise ValueError(f"Stage 0 tasks do not match the frozen 2/0/2 design: {tasks}")

    profiles = {
        profile.name: (profile.use_measured_native_latency, int(profile.added_latency_ms))
        for profile in cfg.latency_profiles
    }
    expected_profiles = {
        ("native" if delay == 0 else f"native_plus_{delay}"): (True, delay)
        for delay in EXPECTED_DELAYS_MS
    }
    if profiles != expected_profiles:
        raise ValueError(f"Stage 0 latency profiles do not match the frozen grid: {profiles}")


def stage0_plans(cfg: BenchmarkConfig) -> list[Stage0Plan]:
    validate_stage0_config(cfg)
    assert cfg.stage0 is not None
    plans = []
    index = 1
    for task in cfg.stage0.tasks:
        for method in cfg.stage0.methods:
            for delay in cfg.stage0.added_delays_ms:
                for seed in cfg.stage0.seeds:
                    plans.append(
                        Stage0Plan(
                            run_id=f"C{index:03d}",
                            task=task,
                            execution_method=method,
                            added_delay_ms=delay,
                            seed=seed,
                            fixed_horizon=cfg.stage0.fixed_horizon,
                        )
                    )
                    index += 1
    if len(plans) != 96:
        raise ValueError(f"Stage 0 must expand to 96 episodes, got {len(plans)}")
    return plans


def stage0_refinement_plans(cfg: BenchmarkConfig) -> list[Stage0Plan]:
    """Build the credit-conscious 25/50/75 ms follow-up on native-viable cells."""
    validate_stage0_config(cfg)
    assert cfg.stage0 is not None
    tasks = {task.task_key: task for task in cfg.stage0.tasks}
    plans = []
    index = 1
    for task_key, method in REFINEMENT_CELLS:
        task = tasks[task_key]
        for delay in REFINEMENT_DELAYS_MS:
            for seed in REFINEMENT_SEEDS:
                plans.append(
                    Stage0Plan(
                        run_id=f"R{index:03d}",
                        task=task,
                        execution_method=method,
                        added_delay_ms=delay,
                        seed=seed,
                        fixed_horizon=cfg.stage0.fixed_horizon,
                        stage=REFINEMENT_STAGE,
                        episode_prefix=REFINEMENT_STAGE,
                    )
                )
                index += 1
    if len(plans) != 18:
        raise ValueError(f"Stage 0 refinement must expand to 18 episodes, got {len(plans)}")
    return plans


def environment_fingerprint(cfg: BenchmarkConfig, plan: Stage0Plan) -> str:
    payload = {
        "repository_revision": cfg.repository_revision,
        "checkpoint_revision": cfg.checkpoint_revision,
        "dataset_revision": cfg.dataset_revision,
        "control_mode": cfg.control_mode,
        "obs_type": cfg.obs_type,
        "camera_name": cfg.camera_name,
        "observation_width": cfg.observation_width,
        "observation_height": cfg.observation_height,
        "init_states": cfg.init_states,
        "num_steps_wait": cfg.num_steps_wait,
        "task": plan.task_ref,
        "task_name": plan.task.task_name,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def manifest_row(cfg: BenchmarkConfig, plan: Stage0Plan) -> dict[str, Any]:
    return {
        "run_id": plan.run_id,
        "stage": plan.stage,
        "task_key": plan.task.task_key,
        "task_group_key": plan.task.task_group_key,
        "task_group_label": plan.task.task_group_label,
        "suite": plan.task.suite,
        "task_id": plan.task.task_id,
        "task_name": plan.task.task_name,
        "execution_method": plan.execution_method,
        "delay_condition": "Native" if plan.added_delay_ms == 0 else f"Native + {plan.added_delay_ms} ms",
        "added_delay_ms": plan.added_delay_ms,
        "seed": plan.seed,
        "n_action_steps": cfg.policy_n_action_steps,
        "fixed_horizon": plan.fixed_horizon,
        "latency_profile": plan.latency_profile,
        "episode_id": plan.episode_id,
        "repository_revision": cfg.repository_revision,
        "model_revision": cfg.checkpoint_revision,
        "environment_fingerprint": environment_fingerprint(cfg, plan),
    }


def manifest_rows(cfg: BenchmarkConfig) -> list[dict[str, Any]]:
    return [manifest_row(cfg, plan) for plan in stage0_plans(cfg)]


def manifest_rows_for_plans(
    cfg: BenchmarkConfig, plans: Iterable[Stage0Plan]
) -> list[dict[str, Any]]:
    return [manifest_row(cfg, plan) for plan in plans]


def summary_metadata(cfg: BenchmarkConfig, plan: Stage0Plan, gpu_id: str | None) -> dict[str, Any]:
    row = manifest_row(cfg, plan)
    row.pop("episode_id")
    row.pop("latency_profile")
    return {
        **row,
        "base_task_id": plan.task.task_id,
        "base_task_name": plan.task.task_name,
        "scene_condition": "ID",
        "perturbation_key": None,
        "perturbation_label": None,
        "mechanism_group_key": None,
        "mechanism_group_label": None,
        "gpu_id": gpu_id,
    }


def _success_rate(rows: Iterable[dict[str, Any]]) -> float:
    values = [int(bool(row["success"])) for row in rows]
    return sum(values) / len(values) if values else float("nan")


def select_high_delay(
    rows: list[dict[str, Any]],
    delays_ms: Iterable[int] = EXPECTED_DELAYS_MS,
) -> dict[str, Any]:
    """Apply the frozen ID-only d* rule to complete Stage 0 episode rows."""
    delays = tuple(int(delay) for delay in delays_ms)
    if not delays or delays[0] != 0 or len(set(delays)) != len(delays):
        raise ValueError(f"delay grid must start at 0 with unique values, got {delays}")
    native_rows = [row for row in rows if int(row["added_delay_ms"]) == 0]
    native_cells: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in native_rows:
        key = (row["task_key"], row["execution_method"])
        native_cells.setdefault(key, []).append(row)
    viable_cells = {
        key for key, cell_rows in native_cells.items() if sum(bool(r["success"]) for r in cell_rows) >= 1
    }
    if len(viable_cells) < 2:
        raise ValueError(f"Stage 0 requires at least 2 viable task x method cells, got {len(viable_cells)}")

    def eligible(delay: int) -> list[dict[str, Any]]:
        return [
            row
            for row in rows
            if int(row["added_delay_ms"]) == delay
            and (row["task_key"], row["execution_method"]) in viable_cells
        ]

    native_success = _success_rate(eligible(0))
    curve = []
    for delay in delays:
        delay_rows = eligible(delay)
        success = _success_rate(delay_rows)
        curve.append(
            {
                "added_delay_ms": delay,
                "success": success,
                "drop_from_native": native_success - success,
                "successful_episodes": sum(bool(row["success"]) for row in delay_rows),
                "episodes": len(delay_rows),
            }
        )

    candidates = [row for row in curve if row["added_delay_ms"] > 0]
    primary = [
        row
        for row in candidates
        if row["drop_from_native"] >= 0.20
        and row["success"] >= 0.25
        and row["successful_episodes"] >= 1
    ]
    saturated = False
    weak = False
    if primary:
        selected = min(primary, key=lambda row: row["added_delay_ms"])
        reason = "primary_rule"
    else:
        nonsaturated = [row for row in candidates if row["success"] >= 0.25]
        if nonsaturated:
            selected = sorted(
                nonsaturated,
                key=lambda row: (-row["drop_from_native"], row["added_delay_ms"]),
            )[0]
            reason = "fallback_largest_drop_with_25pct_success"
        else:
            meaningful = [row for row in candidates if row["drop_from_native"] >= 0.10]
            if meaningful:
                selected = min(meaningful, key=lambda row: row["added_delay_ms"])
                saturated = True
                reason = "fallback_saturated_smallest_10pp_drop"
            else:
                selected = max(candidates, key=lambda row: row["added_delay_ms"])
                weak = True
                reason = (
                    "fallback_weak_use_700ms"
                    if selected["added_delay_ms"] == 700
                    else "fallback_weak_use_largest_delay"
                )

    return {
        "low_added_delay_ms": 0,
        "high_added_delay_ms": selected["added_delay_ms"],
        "selection_used_ood_results": False,
        "calibration_saturated": saturated,
        "calibration_weak": weak,
        "selection_reason": reason,
        "viable_task_method_cells": len(viable_cells),
        "native_success": native_success,
        "selected_delay_success": selected["success"],
        "selected_delay_drop": selected["drop_from_native"],
        "curve": curve,
    }


def plan_asdict(plan: Stage0Plan) -> dict[str, Any]:
    data = asdict(plan)
    data["task"] = plan.task_ref
    data["task_name"] = plan.task.task_name
    data["latency_profile"] = plan.latency_profile
    data["episode_id"] = plan.episode_id
    return data
