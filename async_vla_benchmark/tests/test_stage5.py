import pytest

from async_vla_benchmark.benchmark.stage5 import (
    NATIVE_CHUNK_SIZE, PREFERRED_COVERAGES, SEEDS_5A, SEEDS_5B,
    stage5a_manifest, stage5b_manifest, validate_manifest_5a, validate_manifest_5b,
)

PROVENANCE = {"git_sha": "a" * 40, "libero_plus_git_sha": "b" * 40}


def test_stage5a_manifest_when_only_native_allowed():
    rows = stage5a_manifest(PROVENANCE, coverages=[8])
    assert len(rows) == 2 * 1 * 2 * 5  # 2 tasks, 1 coverage, 2 delays, 5 seeds
    assert {r.seed for r in rows} == set(SEEDS_5A)
    assert {r.scene for r in rows} == {"id"}
    assert {r.configured_action_coverage for r in rows} == {8}
    assert all(r.request_threshold_actions == 4 for r in rows)
    validate_manifest_5a(rows)


def test_stage5a_manifest_full_candidate_set():
    rows = stage5a_manifest(PROVENANCE)
    assert len(rows) == 2 * len(PREFERRED_COVERAGES) * 2 * 5
    assert {r.seed for r in rows} == set(SEEDS_5A)
    validate_manifest_5a(rows)


def test_stage5b_manifest_64_episodes():
    rows = stage5b_manifest(PROVENANCE, selected_coverage=8)
    assert len(rows) == 64
    assert {r.seed for r in rows} == set(SEEDS_5B)
    assert {r.scene for r in rows} == {"id", "ood"}
    validate_manifest_5b(rows, 8)


def test_stage5b_manifest_rejects_wrong_coverage():
    rows = stage5b_manifest(PROVENANCE, selected_coverage=8)
    rows[0] = rows[0].__class__(**{**rows[0].__dict__, "configured_action_coverage": 12})
    with pytest.raises(ValueError):
        validate_manifest_5b(rows, 8)
