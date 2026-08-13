"""Stage 1 LIBERO-Plus OOD x latency matrix."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .config import BenchmarkConfig, Stage0TaskConfig, Stage1PerturbationConfig
from .ood_tasks import TaskVariant, find_variants


EXPECTED_POLICY = "lerobot/pi05_libero_finetuned"
EXPECTED_METHODS = ("naive_async", "rtc")
EXPECTED_LATENCY_CONDITIONS = ("native", "native_plus_dstar")
EXPECTED_FIXED_HORIZON = 10
EXPECTED_STAGE0_TASK_REFS = ("libero_spatial:2", "libero_goal:0", "libero_10:2")


@dataclass(frozen=True)
class Stage1Plan:
    run_id: str
    task: Stage0TaskConfig
    perturbation: Stage1PerturbationConfig
    variant: TaskVariant
    execution_method: str
    latency_condition: str
    added_delay_ms: int
    seed: int
    fixed_horizon: int
    stage: str = "stage1_libero_plus"

    @property
    def base_task_ref(self) -> str:
        return f"{self.task.suite}:{self.task.task_id}"

    @property
    def variant_task_ref(self) -> str:
        return f"{self.task.suite}:{self.variant.task_id}"

    @property
    def latency_profile(self) -> str:
        return "native" if self.added_delay_ms == 0 else f"native_plus_{self.added_delay_ms}"

    @property
    def episode_id(self) -> str:
        return (
            f"stage1_{self.run_id}_{self.task.suite}_base{self.task.task_id}_"
            f"plus{self.variant.task_id}_{self.perturbation.key}_"
            f"{self.execution_method}_{self.latency_profile}_h{self.fixed_horizon}_s{self.seed}"
        )


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def read_selected_high_delay(path: Path | str) -> int:
    payload = json.loads(Path(path).read_text())
    delay = int(payload["high_added_delay_ms"])
    if delay <= 0:
        raise ValueError(f"Stage 1 requires a positive frozen d*, got {delay}")
    if payload.get("selection_used_ood_results") is not False:
        raise ValueError("Stage 1 d* must come from Stage 0 ID-only selection")
    return delay


def validate_stage1_config(cfg: BenchmarkConfig) -> None:
    if cfg.stage1 is None:
        raise ValueError("config has no stage1 section")
    if cfg.repository_revision is None:
        raise ValueError("Stage 1 requires a pinned LeRobot repository_revision")
    if cfg.checkpoint_revision is None:
        raise ValueError("Stage 1 requires a pinned checkpoint_revision")
    if cfg.policy_checkpoint != EXPECTED_POLICY:
        raise ValueError(f"Stage 1 policy must be {EXPECTED_POLICY}, got {cfg.policy_checkpoint}")
    if cfg.policy_n_action_steps != 10:
        raise ValueError("Stage 1 requires policy_n_action_steps=10")
    if cfg.max_parallel_tasks != 1:
        raise ValueError("Stage 1 requires max_parallel_tasks=1")
    if not cfg.rtc.enabled:
        raise ValueError("Stage 1 requires RTC to be enabled")

    stage1 = cfg.stage1
    if tuple(stage1.methods) != EXPECTED_METHODS:
        raise ValueError(f"Stage 1 methods must be {EXPECTED_METHODS}, got {stage1.methods}")
    if tuple(stage1.latency_conditions) != EXPECTED_LATENCY_CONDITIONS:
        raise ValueError(
            f"Stage 1 latency conditions must be {EXPECTED_LATENCY_CONDITIONS}, "
            f"got {stage1.latency_conditions}"
        )
    if stage1.fixed_horizon != EXPECTED_FIXED_HORIZON:
        raise ValueError("Stage 1 uses the frozen h=10 execution setting")
    if len(stage1.perturbations) != 7:
        raise ValueError(
            f"Stage 1 requires exactly seven perturbation families, got "
            f"{len(stage1.perturbations)}"
        )
    task_refs = tuple(f"{task.suite}:{task.task_id}" for task in stage1.tasks)
    if task_refs != EXPECTED_STAGE0_TASK_REFS:
        raise ValueError(f"Stage 1 tasks must reuse Stage 0 2/0/2 tasks, got {task_refs}")


def _variants_by_suite_from_runtime(
    tasks: Sequence[Stage0TaskConfig],
    perturbations: Sequence[Stage1PerturbationConfig],
    difficulty_level: int | None,
) -> dict[tuple[str, str], list[TaskVariant]]:
    resolved = {}
    for task in tasks:
        for perturbation in perturbations:
            variants = find_variants(task.suite, perturbation.category, difficulty_level)
            resolved[(task.suite, perturbation.key)] = variants
    return resolved


def _select_variant(
    task: Stage0TaskConfig,
    perturbation: Stage1PerturbationConfig,
    variants_by_suite: Mapping[tuple[str, str], Sequence[TaskVariant]],
) -> TaskVariant:
    variants = list(variants_by_suite.get((task.suite, perturbation.key), ()))
    if not variants:
        raise ValueError(
            f"No LIBERO-Plus variants found for suite={task.suite!r}, "
            f"category={perturbation.category!r}"
        )
    # Pick the first classified variant for the category/difficulty. The live
    # runner verifies the resolved task name before executing, so a mapping drift
    # fails before producing OOD results.
    return sorted(variants, key=lambda variant: variant.task_id)[0]


def stage1_plans(
    cfg: BenchmarkConfig,
    *,
    high_delay_ms: int | None = None,
    variants_by_suite: Mapping[tuple[str, str], Sequence[TaskVariant]] | None = None,
) -> list[Stage1Plan]:
    validate_stage1_config(cfg)
    assert cfg.stage1 is not None
    if high_delay_ms is None:
        high_delay_ms = read_selected_high_delay(cfg.stage1.stage0_delay_selection_file)
    if variants_by_suite is None:
        variants_by_suite = _variants_by_suite_from_runtime(
            cfg.stage1.tasks,
            cfg.stage1.perturbations,
            cfg.stage1.difficulty_level,
        )

    plans: list[Stage1Plan] = []
    index = 1
    for task in cfg.stage1.tasks:
        for perturbation in cfg.stage1.perturbations:
            variant = _select_variant(task, perturbation, variants_by_suite)
            for method in cfg.stage1.methods:
                for latency_condition in cfg.stage1.latency_conditions:
                    added_delay = 0 if latency_condition == "native" else high_delay_ms
                    for seed in cfg.stage1.seeds:
                        plans.append(
                            Stage1Plan(
                                run_id=f"S1{index:04d}",
                                task=task,
                                perturbation=perturbation,
                                variant=variant,
                                execution_method=method,
                                latency_condition=latency_condition,
                                added_delay_ms=added_delay,
                                seed=seed,
                                fixed_horizon=cfg.stage1.fixed_horizon,
                            )
                        )
                        index += 1
    expected = (
        len(cfg.stage1.tasks)
        * len(cfg.stage1.perturbations)
        * len(cfg.stage1.methods)
        * len(cfg.stage1.latency_conditions)
        * len(cfg.stage1.seeds)
    )
    if len(plans) != expected:
        raise ValueError(f"Stage 1 expanded to {len(plans)} episodes, expected {expected}")
    return plans


def environment_fingerprint(cfg: BenchmarkConfig, plan: Stage1Plan) -> str:
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
        "base_task": plan.base_task_ref,
        "base_task_name": plan.task.task_name,
        "libero_plus_task": plan.variant_task_ref,
        "libero_plus_task_name": plan.variant.name,
        "perturbation": plan.perturbation.category,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def manifest_row(cfg: BenchmarkConfig, plan: Stage1Plan) -> dict[str, Any]:
    return {
        "run_id": plan.run_id,
        "stage": plan.stage,
        "task_key": plan.task.task_key,
        "task_group_key": plan.task.task_group_key,
        "task_group_label": plan.task.task_group_label,
        "suite": plan.task.suite,
        "base_task_id": plan.task.task_id,
        "base_task_name": plan.task.task_name,
        "libero_plus_task_id": plan.variant.task_id,
        "libero_plus_task_name": plan.variant.name,
        "perturbation_key": plan.perturbation.key,
        "perturbation_label": plan.perturbation.label,
        "perturbation_category": plan.perturbation.category,
        "perturbation_difficulty_level": plan.variant.difficulty_level,
        "execution_method": plan.execution_method,
        "latency_condition": plan.latency_condition,
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


def manifest_rows(cfg: BenchmarkConfig, plans: Iterable[Stage1Plan]) -> list[dict[str, Any]]:
    return [manifest_row(cfg, plan) for plan in plans]


def summary_metadata(cfg: BenchmarkConfig, plan: Stage1Plan, gpu_id: str | None) -> dict[str, Any]:
    row = manifest_row(cfg, plan)
    row.pop("episode_id")
    row.pop("latency_profile")
    return {
        **row,
        "task_id": plan.variant.task_id,
        "task_name": plan.variant.name,
        "scene_condition": "LIBERO-Plus",
        "mechanism_group_key": plan.perturbation.key,
        "mechanism_group_label": plan.perturbation.label,
        "gpu_id": gpu_id,
    }


def plan_asdict(plan: Stage1Plan) -> dict[str, Any]:
    data = asdict(plan)
    data["base_task_ref"] = plan.base_task_ref
    data["variant_task_ref"] = plan.variant_task_ref
    data["latency_profile"] = plan.latency_profile
    data["episode_id"] = plan.episode_id
    return data
