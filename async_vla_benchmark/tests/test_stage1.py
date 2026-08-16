import json
import tempfile
from pathlib import Path

import pytest

from async_vla_benchmark.benchmark.stage0 import STAGE0_TASKS
from async_vla_benchmark.benchmark.stage1 import (
    PERTURBATIONS,
    interaction,
    load_selected_delay,
    resolve_variants,
    stage1_manifest,
)


def _resolved():
    classification, names = {}, {}
    next_id = 1
    for task in STAGE0_TASKS:
        entries, suite_names = [], []
        for perturbation in PERTURBATIONS:
            # Include two candidates to exercise difficulty and ID tie-breaking.
            for difficulty in (3, 2):
                name = f"{task.expected_task_name}__{perturbation.key}__d{difficulty}"
                entries.append({"id": next_id, "name": name, "category": perturbation.official_category, "difficulty_level": difficulty})
                while len(suite_names) < next_id:
                    suite_names.append(f"unused_{len(suite_names)}")
                suite_names[next_id - 1] = name
                next_id += 1
        classification[task.suite] = entries
        names[task.suite] = suite_names
    return resolve_variants(classification, names)


def test_resolver_produces_21_level_two_variants():
    rows = _resolved()
    assert len(rows) == 21
    assert all(row.difficulty_level == 2 for row in rows)


def test_resolver_ignores_unscored_variants():
    classification, names = {}, {}
    next_id = 1
    for task in STAGE0_TASKS:
        entries, suite_names = [], []
        for perturbation in PERTURBATIONS:
            for difficulty in (None, 2):
                name = f"{task.expected_task_name}__{perturbation.key}__d{difficulty}"
                entries.append({"id": next_id, "name": name, "category": perturbation.official_category, "difficulty_level": difficulty})
                while len(suite_names) < next_id:
                    suite_names.append(f"unused_{len(suite_names)}")
                suite_names[next_id - 1] = name
                next_id += 1
        classification[task.suite] = entries
        names[task.suite] = suite_names
    rows = resolve_variants(classification, names)
    assert len(rows) == 21
    assert all(row.difficulty_level == 2 for row in rows)


def test_manifest_is_frozen_480_row_design():
    provenance = {"git_sha": "g", "lerobot_git_sha": "l", "libero_plus_git_sha": "p", "model_revision": "m"}
    rows = stage1_manifest(_resolved(), 200, provenance)
    assert len(rows) == 480
    assert sum(row.scene_condition == "ood" for row in rows) == 420
    assert sum(row.scene_condition == "id" for row in rows) == 60
    assert sum(row.reuse_stage0 for row in rows) == 24
    assert sum(row.scene_condition == "id" and not row.reuse_stage0 for row in rows) == 36


def test_wrong_delay_is_rejected():
    provenance = {"git_sha": "g", "lerobot_git_sha": "l", "libero_plus_git_sha": "p", "model_revision": "m"}
    with pytest.raises(ValueError):
        stage1_manifest(_resolved(), 300, provenance)


def test_selected_delay_must_be_id_only():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "selected.json"
        path.write_text(json.dumps({"high_added_delay_ms": 200, "selection_used_ood_results": False}))
        assert load_selected_delay(path) == 200


def test_interaction_definition():
    assert abs(interaction(0.8, 0.6, 0.7, 0.3) - (-0.2)) < 1e-12
