#!/usr/bin/env python3
"""Validate Stage 5A or 5B manifests, results, and analysis artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv
from async_vla_benchmark.benchmark.stage4 import EXECUTION_METHOD, POLICY_FAMILY, TASKS
from async_vla_benchmark.benchmark.stage5 import (
    NATIVE_CHUNK_SIZE, PREFERRED_COVERAGES, SEEDS_5A, SEEDS_5B,
    validate_manifest_5a, validate_manifest_5b,
)


def _validate_5a(audit_path: Path, manifest_path: Path, output_dir: Path, selected_path: Path | None = None) -> int:
    errors = []
    rows = read_csv(manifest_path)
    report = {"phase": "5a", "manifest_rows": len(rows)}

    if not audit_path.exists():
        errors.append("missing stage5_openvla_coverage_capability_audit.json")
    else:
        audit = json.loads(audit_path.read_text())
        if audit.get("model_native_output_horizon") != NATIVE_CHUNK_SIZE:
            errors.append("audit reports a native horizon other than 8")
        if audit.get("coverage_sweep_gt_native_allowed"):
            errors.append("audit permits >8 coverage; this gate must be closed before validation")

    if rows:
        try:
            validate_manifest_5a(rows)
        except Exception as exc:
            errors.append(str(exc))
        if {int(r["configured_action_coverage"]) for r in rows} != {8}:
            errors.append("5A manifest contains a coverage other than the audited native 8")
        if {int(r["seed"]) for r in rows} != set(SEEDS_5A):
            errors.append("5A seed set is not 46..50")
        if any(r["scene"] != "id" for r in rows):
            errors.append("5A contains non-ID scenes")

    result_path = output_dir / "stage5a_episode_results.csv"
    results = read_csv(result_path) if result_path.exists() else []
    report["result_rows"] = len(results)
    if rows and not results:
        errors.append("manifest is non-empty but no results file exists")
    for r in results:
        required = {
            "policy_family": POLICY_FAMILY,
            "execution_method": EXECUTION_METHOD,
            "native_chunk_size": "8",
            "model_native_output_horizon": "8",
            "coverage_is_single_inference_native": "True",
        }
        for field, expected in required.items():
            if str(r.get(field)) != expected:
                errors.append(f"{r['run_id']}: {field} mismatch")

    provenance = output_dir / "stage5a_policy_provenance.json"
    if results and not provenance.exists():
        errors.append("missing stage5a_policy_provenance.json")

    if selected_path is None:
        selected_path = output_dir / "analysis" / "stage5a_selected_operating_point.json"
    if not selected_path.exists():
        errors.append("missing stage5a_selected_operating_point.json")
    elif not json.loads(selected_path.read_text()).get("selected_without_ood_outcomes"):
        errors.append("5A operating point must be selected without OOD outcomes")

    report["status"] = "fail" if errors else "pass"
    report["errors"] = sorted(set(errors))
    report["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    out = output_dir / "stage5a_validation.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


def _validate_5b(selected_path: Path, manifest_path: Path, output_dir: Path) -> int:
    errors = []
    rows = read_csv(manifest_path)
    report = {"phase": "5b", "manifest_rows": len(rows)}

    selected = json.loads(selected_path.read_text()) if selected_path.exists() else {}
    if not selected.get("proceed_to_stage5b", False):
        if rows:
            errors.append("Stage 5B manifest is non-empty but 5A did not proceed to 5B")
        report["status"] = "pass" if not errors else "fail"
        report["result_rows"] = 0
        report["errors"] = sorted(set(errors))
        report["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        (output_dir / "stage5b_validation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 1 if errors else 0

    coverage = int(selected["configured_action_coverage"])
    try:
        validate_manifest_5b(rows, coverage)
    except Exception as exc:
        errors.append(str(exc))

    if len(rows) != 64:
        errors.append(f"Stage 5B manifest must contain 64 rows, got {len(rows)}")
    if {int(r["seed"]) for r in rows} != set(SEEDS_5B):
        errors.append("5B seeds must be 51..58")
    for task in TASKS:
        for scene in ("id", "ood"):
            for delay in (0, 200):
                cell = [r for r in rows if r["task_key"] == task and r["scene_condition"] == scene and int(r["added_delay_ms"]) == delay]
                if len(cell) != 8:
                    errors.append(f"{task}/{scene}/d{delay}: expected 8 seeds, got {len(cell)}")

    result_path = output_dir / "stage5b_episode_results.csv"
    results = read_csv(result_path) if result_path.exists() else []
    report["result_rows"] = len(results)
    if len(results) != 64 and coverage == NATIVE_CHUNK_SIZE:
        errors.append(f"expected 64 5B results, got {len(results)}")
    for r in results:
        if str(r.get("configured_action_coverage")) != str(coverage):
            errors.append(f"{r['run_id']}: configured coverage differs from selected")

    report["status"] = "fail" if errors else "pass"
    report["errors"] = sorted(set(errors))
    out = output_dir / "stage5b_validation.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=("a", "b"), required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--audit", type=Path)
    p.add_argument("--selected", type=Path)
    args = p.parse_args()
    if args.phase == "a":
        return _validate_5a(args.audit or Path(""), args.manifest, args.output_dir, args.selected)
    return _validate_5b(args.selected or Path(""), args.manifest, args.output_dir)


if __name__ == "__main__": raise SystemExit(main())
