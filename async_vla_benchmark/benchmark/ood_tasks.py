"""Lookup helpers for LIBERO-plus's task_classification.json.

LIBERO-plus does not add a separate perturbation API: each perturbation
category/difficulty is baked into a specific `task_id` within a suite (see
`environment.make_libero_plus_env`). `task_classification.json`, shipped
inside the installed LIBERO-plus package, is the only map from
category/difficulty back to a `task_id`.

CONFIRMED via scripts/diagnose_libero_plus.py against a running LIBERO-plus
install (2026-08-05, libero_spatial, task_id=0): the JSON's numeric `id` field
is 1-indexed while `_get_suite(suite_name).tasks[task_id]`/`task_id` is
0-indexed — `task_id = id - 1`, not `task_id = id`. Verified by exact name
match: json id=1's `name` ("pick_up_the_black_bowl_between_the_plate_and_the_
ramekin_and_place_it_on_the_plate_table_1") equals the live task name at
task_id=0. `TaskVariant.task_id` below already applies this offset; use it,
not `.id`, when calling `make_libero_plus_env`.
"""

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class TaskClassificationUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class TaskVariant:
    id: int  # raw 1-indexed id as stored in task_classification.json
    name: str
    category: str
    difficulty_level: int | None

    @property
    def task_id(self) -> int:
        """0-indexed task_id to pass to make_libero_plus_env / _get_suite(...).tasks[...]."""
        return self.id - 1


def find_task_classification_path() -> Path:
    """Locate task_classification.json inside the installed `libero` package.

    Mirrors the `benchmark_root` convention baked into ~/.libero/config.yaml
    at image-build time (see Dockerfile.modal.libero_plus): the installed
    `libero` top-level package's directory contains a nested `libero/`
    package directory, under which `benchmark/task_classification.json` lives.
    """
    try:
        import libero
    except ImportError as exc:
        raise TaskClassificationUnavailable(
            "`libero` is not importable; install the LIBERO-plus fork first."
        ) from exc

    # LIBERO-plus is imported via PYTHONPATH (see Dockerfile.modal.libero_plus),
    # not a real package install, so it resolves as a namespace package with
    # `__file__ = None`; use `__path__` instead in that case.
    if getattr(libero, "__file__", None):
        package_dir = Path(os.path.dirname(libero.__file__))
    else:
        package_dir = Path(next(iter(libero.__path__)))
    root = package_dir / "libero"
    path = root / "benchmark" / "task_classification.json"
    if not path.exists():
        raise TaskClassificationUnavailable(
            f"task_classification.json not found at {path}. Is the installed `libero` "
            "package the LIBERO-plus fork (not vanilla hf-libero)?"
        )
    return path


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    path = find_task_classification_path()
    with open(path) as f:
        return json.load(f)


def list_suites() -> list[str]:
    """Suite names present in task_classification.json (top-level keys)."""
    return sorted(_load_raw().keys())


def list_variants(suite_name: str) -> list[TaskVariant]:
    """All classified task variants for one suite, e.g. 'libero_spatial'.

    Does not include the suite's unperturbed base tasks (e.g. task_id 0-9 for
    libero_spatial's 10 base tasks appear to be absent from the JSON
    entirely, based on task_id=0 having no entry) — only perturbation
    variants are classified here.
    """
    raw = _load_raw()
    if suite_name not in raw:
        raise ValueError(
            f"Suite '{suite_name}' not found in task_classification.json. "
            f"Available: {', '.join(sorted(raw.keys()))}"
        )
    variants = []
    for entry in raw[suite_name]:
        difficulty = entry.get("difficulty_level")
        variants.append(
            TaskVariant(
                id=int(entry["id"]),
                name=str(entry["name"]),
                category=str(entry["category"]),
                difficulty_level=None if difficulty is None else int(difficulty),
            )
        )
    return variants


def list_categories(suite_name: str) -> list[str]:
    return sorted({variant.category for variant in list_variants(suite_name)})


def find_variants(
    suite_name: str,
    category: str,
    difficulty_level: int | None = None,
) -> list[TaskVariant]:
    """Task variants matching a perturbation category (and optional difficulty).

    `category` matches case-insensitively against the JSON's `category` field
    (e.g. "Objects Layout", "Camera Viewpoints" — see list_categories() for the
    exact strings shipped for a given suite). Use the returned variants'
    `.task_id` (not `.id`) when building an env.
    """
    variants = [
        v for v in list_variants(suite_name) if v.category.lower() == category.lower()
    ]
    if difficulty_level is not None:
        variants = [v for v in variants if v.difficulty_level == difficulty_level]
    return sorted(variants, key=lambda v: v.task_id)


def verify_task_id_mapping(suite_name: str, variant: TaskVariant, live_task_name: str) -> bool:
    """Cross-check the id-1 == task_id mapping against a live suite.

    Call with `live_task_name` = `environment.get_task_info(env, suite_name,
    variant.task_id).task_name` after building an env with
    `task_id=variant.task_id`. Returns True only if the live task's name
    matches what task_classification.json claims for that variant.
    """
    return live_task_name == variant.name
