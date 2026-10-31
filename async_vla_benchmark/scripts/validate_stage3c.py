#!/usr/bin/env python3
"""Fail-closed Stage 3C gate and frozen Stage 3D handoff writer."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage3c import (
    AUDIT_ROWS, ENV_CONSTRUCTION_SEED, FINGERPRINT_METHOD,
    INITIALIZATION_INDICES, REPEAT_IDS, TASKS, VALIDATED_ROWS,
    assert_frozen_variants,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(rows):
    errors = []
    expected_keys = {
        (task, scene, str(index), str(repeat))
        for task in TASKS for scene in ("id", "ood")
        for index in INITIALIZATION_INDICES for repeat in REPEAT_IDS
    }
    keys = {
        (r.get("task_key"), r.get("scene_condition"),
         r.get("requested_initialization_index"), r.get("repeat_id"))
        for r in rows
    }
    if len(rows) != AUDIT_ROWS or keys != expected_keys:
        errors.append(f"audit must contain exactly {AUDIT_ROWS} unique required reset rows")
    groups = defaultdict(list)
    for row in rows:
        groups[(row.get("task_key"), row.get("scene_condition"),
                row.get("requested_initialization_index"))].append(row)
        if row.get("requested_initialization_index") != row.get("resolved_initialization_index_or_id"):
            errors.append(
                f"{row.get('task_key')}/{row.get('scene_condition')}/"
                f"index={row.get('requested_initialization_index')}: resolved as "
                f"{row.get('resolved_initialization_index_or_id')}"
            )
        if row.get("env_construction_seed") != str(ENV_CONSTRUCTION_SEED):
            errors.append("environment-construction seed is not exactly 0")
        try:
            available = int(row.get("available_initialization_state_count", "0"))
        except ValueError:
            available = 0
        if available < len(INITIALIZATION_INDICES):
            errors.append(
                f"{row.get('task_key')}/{row.get('scene_condition')}: only "
                f"{available} initialization states available; 8 required"
            )
        if row.get("policy_rollout_seed"):
            errors.append("policy/rollout seed present in reset-only audit")
        if row.get("policy_inference_executed") != "False" or row.get("action_steps_executed") != "0":
            errors.append("policy inference or action stepping detected")
        if row.get("fingerprint_schema_version") != FINGERPRINT_METHOD:
            errors.append("noncanonical fingerprint method")
    certified = []
    for key, group in groups.items():
        repeats = {r.get("repeat_id") for r in group}
        fingerprints = {r.get("initial_state_fingerprint") for r in group}
        if repeats != {str(x) for x in REPEAT_IDS} or len(group) != len(REPEAT_IDS):
            errors.append(f"{key}: expected exactly 3 repeats")
        if len(fingerprints) != 1 or "" in fingerprints:
            errors.append(f"{key}: within-index determinism failed")
        if len(group) == len(REPEAT_IDS) and len(fingerprints) == 1 and "" not in fingerprints:
            first = group[0]
            certified.append({
                "task_key": key[0], "scene_condition": key[1],
                "variant_name_or_id": first["variant_name_or_id"],
                "requested_initialization_index": key[2],
                "resolved_initialization_index_or_id": first["resolved_initialization_index_or_id"],
                "available_initialization_state_count": first["available_initialization_state_count"],
                "initial_state_fingerprint": next(iter(fingerprints)),
                "fingerprint_schema_version": first["fingerprint_schema_version"],
                "env_construction_seed": first["env_construction_seed"],
                "stage3c_spec_hash": first["stage3c_spec_hash"],
                "benchmark_repo_sha": first["benchmark_repo_sha"],
                "libero_git_sha": first["libero_git_sha"],
                "libero_plus_git_sha": first["libero_plus_git_sha"],
            })
    for task in TASKS:
        for scene in ("id", "ood"):
            values = {
                row["initial_state_fingerprint"] for row in certified
                if row["task_key"] == task and row["scene_condition"] == scene
            }
            if len(values) != len(INITIALIZATION_INDICES):
                errors.append(f"{task}/{scene}: across-index 8/8 distinctness failed")
    return sorted(set(errors)), certified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--frozen-variants", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = read_csv(args.audit) if args.audit.exists() else []
    errors = []
    try:
        assert_frozen_variants(read_csv(args.frozen_variants))
    except Exception as exc:
        errors.append(str(exc))
    gate_errors, certified = validate(rows)
    errors.extend(gate_errors)
    validated = args.output_dir / "stage3c_validated_initializations.csv"
    if not errors and len(certified) == VALIDATED_ROWS:
        certified.sort(key=lambda r: (r["task_key"], r["scene_condition"], int(r["requested_initialization_index"])))
        write_csv(validated, certified)
    elif validated.exists():
        validated.unlink()
    passed = not errors and len(certified) == VALIDATED_ROWS
    report = {
        "stage": "stage3c", "status": "pass" if not errors else "fail",
        "reset_operations": len(rows),
        "deterministic_candidate_initializations": len(certified),
        "validated_initializations": len(certified) if passed else 0,
        "policy_inference_executed": False, "errors": errors,
        "stage3c_spec_sha256": digest(args.spec),
        "stage3c_initialization_audit_csv_sha256": digest(args.audit) if args.audit.exists() else None,
        "stage3c_validated_initializations_csv_sha256": digest(validated) if validated.exists() else None,
    }
    (args.output_dir / "stage3c_initialization_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"audit={len(rows)} validated={len(certified) if passed else 0} errors={len(errors)}")
    if errors:
        print(*(f"ERROR: {error}" for error in errors), sep="\n")
        print("Stage 3C validation failed closed; Stage 3D must not dispatch")
        return 1
    print("Stage 3C validation passed: 144 resets, 48 certified initializations, no policy inference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
