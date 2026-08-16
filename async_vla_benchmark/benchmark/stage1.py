"""Pure Stage 1 design, variant resolution, manifest, and interaction helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .stage0 import STAGE0_TASKS

SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
REUSED_STAGE0_SEEDS: tuple[int, ...] = (0, 1)
EXECUTION_METHODS: tuple[str, ...] = ("naive_async", "rtc")
DELAY_CONDITIONS: tuple[str, ...] = ("low", "high")
N_ACTION_STEPS = 25


@dataclass(frozen=True)
class PerturbationSpec:
    key: str
    label: str
    official_category: str
    mechanism_key: str
    mechanism_label: str


PERTURBATIONS: tuple[PerturbationSpec, ...] = (
    PerturbationSpec("object_layout", "Object layout", "Objects Layout", "trajectory_adaptation", "Trajectory adaptation"),
    PerturbationSpec("robot_initial_state", "Robot initial state", "Robot Initial States", "trajectory_adaptation", "Trajectory adaptation"),
    PerturbationSpec("camera_viewpoint", "Camera viewpoint", "Camera Viewpoints", "perceptual_localization", "Perceptual localization"),
    PerturbationSpec("sensor_noise", "Sensor noise", "Sensor Noise", "perceptual_localization", "Perceptual localization"),
    PerturbationSpec("light_conditions", "Lighting", "Light Conditions", "appearance_invariance", "Appearance invariance"),
    PerturbationSpec("background_textures", "Background texture", "Background Textures", "appearance_invariance", "Appearance invariance"),
    PerturbationSpec("language_instructions", "Language instruction", "Language Instructions", "semantic_grounding", "Semantic grounding"),
)

TASK_GROUP_LABELS = {
    "single_stage_transport": "Single-stage transport",
    "articulated_contact_rich": "Articulated/contact-rich",
    "multi_stage_sequential": "Multi-stage/sequential",
}


@dataclass(frozen=True)
class ResolvedVariant:
    task_key: str
    suite: str
    base_task_id: int
    base_task_name: str
    task_group: str
    perturbation_key: str
    official_category: str
    mechanism_group: str
    classification_id: int
    api_task_index: int
    variant_name: str
    difficulty_level: int


def resolve_variants(
    classification: Mapping[str, Sequence[Mapping[str, object]]],
    suite_names: Mapping[str, Sequence[str]],
) -> list[ResolvedVariant]:
    """Apply the frozen nearest-to-level-2, lowest-ID rule and verify API names."""
    rows: list[ResolvedVariant] = []
    for task in STAGE0_TASKS:
        names = list(suite_names[task.suite])
        for perturbation in PERTURBATIONS:
            candidates = [
                entry
                for entry in classification[task.suite]
                if str(entry["name"]).startswith(task.expected_task_name)
                and str(entry["category"]) == perturbation.official_category
            ]
            if not candidates:
                raise ValueError(
                    f"no variant for {task.task_key}/{perturbation.key}"
                )
            chosen = min(
                candidates,
                key=lambda entry: (
                    abs(int(entry["difficulty_level"]) - 2),
                    int(entry["id"]),
                ),
            )
            name = str(chosen["name"])
            guessed = int(chosen["id"]) - 1
            api_index = guessed if 0 <= guessed < len(names) and names[guessed] == name else names.index(name)
            if names[api_index] != name:
                raise AssertionError(f"API name mismatch for {name}")
            rows.append(
                ResolvedVariant(
                    task.task_key,
                    task.suite,
                    task.task_id,
                    task.expected_task_name,
                    task.task_group,
                    perturbation.key,
                    perturbation.official_category,
                    perturbation.mechanism_key,
                    int(chosen["id"]),
                    api_index,
                    name,
                    int(chosen["difficulty_level"]),
                )
            )
    if len(rows) != 21:
        raise AssertionError(f"expected 21 variants, got {len(rows)}")
    return rows


@dataclass(frozen=True)
class Stage1Plan:
    run_id: str
    git_sha: str
    lerobot_git_sha: str
    libero_plus_git_sha: str
    model_revision: str
    task_key: str
    suite: str
    base_task_id: int
    base_task_name: str
    task_group: str
    scene_condition: str
    perturbation_key: str
    official_category: str
    mechanism_group: str
    classification_id: int | None
    api_task_index: int
    variant_name: str
    difficulty_level: int | None
    execution_method: str
    delay_condition: str
    added_delay_ms: int
    seed: int
    n_action_steps: int
    output_path: str
    reuse_stage0: bool
    source_run_id: str = ""
    status: str = "pending"
    invalid_reason: str = ""


def _run_id(task: str, scene: str, perturbation: str, method: str, delay: str, seed: int) -> str:
    return f"{task}__{scene}__{perturbation}__{method}__{delay}__s{seed}"


def stage1_manifest(
    variants: Sequence[ResolvedVariant],
    high_delay_ms: int,
    provenance: Mapping[str, str],
) -> list[Stage1Plan]:
    if high_delay_ms != 200:
        raise ValueError(f"Stage 1 high delay is frozen at 200 ms, got {high_delay_ms}")
    by_pair = {(v.task_key, v.perturbation_key): v for v in variants}
    if len(by_pair) != 21:
        raise ValueError("resolved variant mapping must contain 21 unique task/perturbation pairs")
    plans: list[Stage1Plan] = []
    for task in STAGE0_TASKS:
        for method in EXECUTION_METHODS:
            for delay in DELAY_CONDITIONS:
                for seed in SEEDS:
                    reuse = seed in REUSED_STAGE0_SEEDS
                    run_id = _run_id(task.task_key, "id", "id", method, delay, seed)
                    source_run_id = f"stage0__{task.task_key}__{method}__d{0 if delay == 'low' else high_delay_ms}__s{seed}" if reuse else ""
                    plans.append(Stage1Plan(
                        run_id, provenance["git_sha"], provenance["lerobot_git_sha"],
                        provenance["libero_plus_git_sha"], provenance["model_revision"],
                        task.task_key, task.suite, task.task_id, task.expected_task_name,
                        task.task_group, "id", "id", "ID", "id", None, task.task_id,
                        task.expected_task_name, None, method, delay,
                        0 if delay == "low" else high_delay_ms, seed, N_ACTION_STEPS,
                        (f"stage0_reuse/episodes/{source_run_id}.json" if reuse else f"episodes/{run_id}.json"), reuse, source_run_id,
                        "pending",
                        "Stage 0 identity metadata incomplete; reuse accepted as documented limitation" if reuse else "",
                    ))
        for perturbation in PERTURBATIONS:
            variant = by_pair[(task.task_key, perturbation.key)]
            for method in EXECUTION_METHODS:
                for delay in DELAY_CONDITIONS:
                    for seed in SEEDS:
                        run_id = _run_id(task.task_key, "ood", perturbation.key, method, delay, seed)
                        plans.append(Stage1Plan(
                            run_id, provenance["git_sha"], provenance["lerobot_git_sha"],
                            provenance["libero_plus_git_sha"], provenance["model_revision"],
                            task.task_key, task.suite, task.task_id, task.expected_task_name,
                            task.task_group, "ood", perturbation.key, perturbation.official_category,
                            perturbation.mechanism_key, variant.classification_id,
                            variant.api_task_index, variant.variant_name, variant.difficulty_level,
                            method, delay, 0 if delay == "low" else high_delay_ms, seed,
                            N_ACTION_STEPS, f"episodes/{run_id}.json", False,
                            "",
                        ))
    validate_manifest(plans, high_delay_ms)
    return plans


def validate_manifest(plans: Sequence[Stage1Plan], high_delay_ms: int = 200) -> None:
    if len(plans) != 480 or len({p.run_id for p in plans}) != 480:
        raise ValueError("manifest must contain 480 unique run IDs")
    if sum(p.scene_condition == "id" for p in plans) != 60:
        raise ValueError("manifest must contain 60 ID rows")
    if sum(p.scene_condition == "ood" for p in plans) != 420:
        raise ValueError("manifest must contain 420 OOD rows")
    if sum(p.reuse_stage0 for p in plans) != 24:
        raise ValueError("manifest must mark exactly 24 Stage 0 rows for reuse")
    if {p.seed for p in plans} != set(SEEDS):
        raise ValueError("manifest seed set is not frozen")
    if any(p.n_action_steps != N_ACTION_STEPS for p in plans):
        raise ValueError("n_action_steps must be 25")
    if any(p.added_delay_ms != (0 if p.delay_condition == "low" else high_delay_ms) for p in plans):
        raise ValueError("delay condition disagrees with frozen d*")


def load_selected_delay(path: Path) -> int:
    payload = json.loads(path.read_text())
    if payload.get("selection_used_ood_results") is not False:
        raise ValueError("selected delay must be based on ID-only results")
    value = int(payload["high_added_delay_ms"])
    if value != 200:
        raise ValueError(f"expected frozen d*=200 ms, got {value}")
    return value


def write_dataclass_csv(path: Path, rows: Iterable[object]) -> None:
    dictionaries = [asdict(row) for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dictionaries[0]))
        writer.writeheader()
        writer.writerows(dictionaries)


def interaction(id_low: float, id_high: float, ood_low: float, ood_high: float) -> float:
    return (ood_high - ood_low) - (id_high - id_low)
