#!/usr/bin/env python3
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from async_vla_benchmark.benchmark.experiment_b import (
    ANALYSIS_STATUS, DELAYS, validate_experiment_a_gate, validate_frozen_variants, validate_manifest,
)
from async_vla_benchmark.benchmark.logging import read_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--experiment-a-gate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args(); errors = []
    gate_hash = validate_experiment_a_gate(args.experiment_a_gate)
    variants = read_csv(args.variants); rows = read_csv(args.manifest)
    frozen_hash = hashlib.sha256(args.variants.read_bytes()).hexdigest()
    try:
        validate_frozen_variants(variants); validate_manifest(rows, variants, frozen_hash, gate_hash)
    except Exception as exc:
        errors.append(str(exc))
    groups = defaultdict(list)
    for row in rows:
        groups[(row["scene_condition"], row["variant_name"], row["seed"])].append(row)
    if len(groups) != 32:
        errors.append(f"expected 32 paired seed groups, got {len(groups)}")
    for key, group in groups.items():
        if {int(row["added_delay_ms"]) for row in group} != set(DELAYS) or len(group) != 2:
            errors.append(f"{key}: incomplete Native/+200 pair")
        identities = {(r["initialization_index_or_id"], r["initial_state_fingerprint_method"], r["initial_state_fingerprint"], r.get("requested_initialization_index"), r.get("resolved_initialization_index_or_id")) for r in group}
        identity = next(iter(identities), ("",) * 5)
        if len(identities) != 1 or any(not value or str(value).startswith("PENDING") for value in identity):
            errors.append(f"{key}: unresolved or unpaired initialization")
        elif identity[3:] not in (("0", "0"), (0, 0)):
            errors.append(f"{key}: initialization is not requested/resolved zero")
    result_path = args.output_dir / "experiment_b_episode_results.csv"
    results = read_csv(result_path) if result_path.exists() else []
    by_id = {row["run_id"]: row for row in results}; manifest_ids = {row["run_id"] for row in rows}
    missing = manifest_ids - set(by_id); invalid = []
    plans = {row["run_id"]: row for row in rows}
    for run_id, result in by_id.items():
        if run_id not in manifest_ids:
            errors.append(f"unexpected result {run_id}"); continue
        if not result.get("status", "").startswith("ok"):
            invalid.append(run_id)
        plan = plans[run_id]
        for field in ("initialization_index_or_id", "initial_state_fingerprint", "initial_state_fingerprint_method", "frozen_variant_csv_sha256", "experiment_a_dispatch_gate_sha256"):
            if result.get(field) != plan.get(field):
                errors.append(f"{run_id}: {field} mismatch")
        if result.get("stage_or_experiment_label") != "experiment_b" or result.get("analysis_status") != ANALYSIS_STATUS:
            errors.append(f"{run_id}: provenance label mismatch")
        if result.get("requested_initialization_index") != "0" or result.get("resolved_initialization_index_or_id") != "0":
            errors.append(f"{run_id}: initialization index is not zero")
        for folder, extension in (("episodes", "json"), ("requests", "parquet"), ("actions", "parquet")):
            path = args.output_dir / folder / f"{run_id}.{extension}"
            if not path.exists():
                errors.append(f"{run_id}: missing {folder}")
            elif extension == "json":
                try: json.loads(path.read_text())
                except Exception: errors.append(f"{run_id}: invalid episode JSON")
    unresolved = []
    invalid_path = args.output_dir / "experiment_b_invalid_episodes.csv"
    if invalid_path.exists():
        unresolved = [row["run_id"] for row in read_csv(invalid_path) if row.get("run_id") not in by_id or not by_id[row["run_id"]].get("status", "").startswith("ok")]
    if missing and not args.allow_incomplete: errors.append(f"{len(missing)} missing results")
    if invalid: errors.append(f"{len(invalid)} invalid result rows")
    if unresolved: errors.append(f"{len(set(unresolved))} unresolved infrastructure failures")
    report = {
        "status": "fail" if errors else ("incomplete_allowed" if missing else "pass"),
        "manifest_rows": len(rows), "result_rows": len(results), "missing_rows": len(missing),
        "invalid_rows": len(invalid), "variant_rows": len(variants),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "frozen_variants_sha256": frozen_hash, "experiment_a_dispatch_gate_sha256": gate_hash,
        "results_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest() if result_path.exists() else None,
        "errors": sorted(set(errors)),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "experiment_b_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"manifest={len(rows)} results={len(results)} missing={len(missing)} invalid={len(invalid)} variants={len(variants)} gate=pass")
    if errors:
        print(*(f"ERROR: {error}" for error in sorted(set(errors))), sep="\n"); return 1
    print("Experiment B validation passed"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
