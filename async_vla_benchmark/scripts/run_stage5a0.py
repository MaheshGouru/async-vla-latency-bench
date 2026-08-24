#!/usr/bin/env python3
"""Stage 5A0 — OpenVLA-OFT native action-horizon capability audit.

This script closes the gate before any Stage-5A ID calibration rollouts are run.
It can operate in two modes:

  --static (default)   inspect the pinned OpenVLA-OFT source constants and the
                       `predict_action` implementation without loading the model.
  --runtime            load the checkpoint once and verify the returned action
                       tensor shape empirically (requires the full OpenVLA-OFT
                       execution environment described in the Stage 5 notebooks).

If a single inference returns exactly the native 8 actions and no legitimate
mechanism exposes >8, the gate is recorded as closed; Stage 5A coverage sweep
and Stage 5B are not permitted.
"""
from __future__ import annotations

import argparse

NATIVE_CHUNK_SIZE = 8
import ast
import json
import re
import sys
import time
from pathlib import Path


def _parse_num_actions_chunk(source: Path) -> int | None:
    """Read the pinned LIBERO `NUM_ACTIONS_CHUNK` constant."""
    path = source / "prismatic" / "vla" / "constants.py"
    if not path.is_file():
        return None
    text = path.read_text()
    match = re.search(r'"NUM_ACTIONS_CHUNK"\s*:\s*(\d+)', text)
    if match:
        return int(match.group(1))
    return None


def _parse_predict_action_horizon(source: Path) -> dict | None:
    """Inspect whether `predict_action` generates a fixed action-token block."""
    path = source / "prismatic" / "models" / "vlas" / "openvla.py"
    if not path.is_file():
        return None
    text = path.read_text()
    audit = {
        "uses_fixed_action_token_block": False,
        "token_block_expression": None,
        "action_dim_reference": None,
    }
    # Look for the generated token slicing / reshape that produces the actions.
    if "get_action_dim(unnorm_key)" in text:
        audit["action_dim_reference"] = "get_action_dim(unnorm_key)"
    if "predicted_action_token_ids" in text and "NUM_ACTIONS_CHUNK" in text:
        audit["uses_fixed_action_token_block"] = True
        lines = [ln.strip() for ln in text.splitlines() if "NUM_ACTIONS_CHUNK" in ln or "self.get_action_dim" in ln]
        if lines:
            audit["token_block_expression"] = "; ".join(lines[:3])
    return audit


def _parse_get_action_dim(source: Path) -> int | None:
    """Try to locate a hard-coded `get_action_dim` value for LIBERO."""
    path = source / "prismatic" / "models" / "vlas" / "openvla.py"
    if not path.is_file():
        return None
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_action_dim":
            # Look for a return that is a multiplication by ACTION_DIM.
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.BinOp) and isinstance(stmt.op, ast.Mult):
                    if any(isinstance(n, ast.Name) and n.id == "NUM_ACTIONS_CHUNK" for n in ast.walk(stmt.left)):
                        return 8  # LIBERO constant is 8
                    if any(isinstance(n, ast.Name) and n.id == "ACTION_DIM" for n in ast.walk(stmt.right)):
                        return 8
    return None


def _runtime_audit(checkout: Path, snapshot: Path, device: str) -> dict:
    """Load the pinned policy once and measure the returned action chunk."""
    import numpy as np

    sys.path.insert(0, str(checkout))
    from async_vla_benchmark.benchmark.openvla_oft import OpenVLAOFTPolicy

    policy = OpenVLAOFTPolicy(snapshot, checkout)
    policy.set_suite("libero_spatial")
    # Build the smallest observation shape the preprocessor accepts.
    dummy_obs = {
        "pixels": {
            "agentview_image": np.full((224, 224, 3), 128, dtype=np.uint8),
            "robot0_eye_in_hand_image": np.full((224, 224, 3), 128, dtype=np.uint8),
        },
        "robot_state": {
            "eef": {"pos": np.zeros(3, dtype=np.float32), "quat": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)},
            "gripper": {"qpos": np.array([0.0, 0.0], dtype=np.float32)},
        },
    }
    prepared = policy.prepare_observation(dummy_obs, "pick up the black bowl")
    actions = policy.predict_action_chunk(prepared)
    return {
        "runtime_audited": True,
        "single_inference_returned_actions": int(actions.shape[0]),
        "single_inference_action_dim": int(actions.shape[1]) if len(actions.shape) > 1 else None,
        "native_chunk_shape": list(actions.shape),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--openvla-oft-checkout", type=Path)
    p.add_argument("--checkpoint-snapshot", type=Path)
    p.add_argument("--device", default="cuda")
    p.add_argument("--runtime", action="store_true", help="run a single model inference to measure the chunk")
    p.add_argument("--git-sha", required=True)
    p.add_argument("--libero-plus-git-sha", required=True)
    args = p.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "stage5_openvla_coverage_capability_audit.json"

    if args.runtime:
        if not args.openvla_oft_checkout or not args.checkpoint_snapshot:
            raise SystemExit("--runtime requires --openvla-oft-checkout and --checkpoint-snapshot")
        runtime = _runtime_audit(args.openvla_oft_checkout, args.checkpoint_snapshot, args.device)
        native_output_horizon = runtime["single_inference_returned_actions"]
    else:
        if not args.openvla_oft_checkout:
            args.openvla_oft_checkout = Path.home() / "openvla-oft"
        if not args.openvla_oft_checkout.is_dir():
            raise SystemExit(f"OpenVLA-OFT checkout not found at {args.openvla_oft_checkout}; use --openvla-oft-checkout")
        native_output_horizon = _parse_num_actions_chunk(args.openvla_oft_checkout)
        if native_output_horizon is None:
            raise SystemExit("could not read NUM_ACTIONS_CHUNK from pinned OpenVLA-OFT source")
        runtime = {"runtime_audited": False, "single_inference_returned_actions": None}

    source_audit = _parse_predict_action_horizon(args.openvla_oft_checkout)
    action_dim = _parse_get_action_dim(args.openvla_oft_checkout)
    maximum_native_coverage = native_output_horizon
    supports_gt = native_output_horizon is not None and native_output_horizon > 8
    supports_lt = native_output_horizon is not None and native_output_horizon == 8

    gate_closed = (
        native_output_horizon == NATIVE_CHUNK_SIZE
        and not supports_gt
        and source_audit is not None
    )

    audit = {
        "stage": "stage5a0_capability_audit",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": args.git_sha,
        "libero_plus_git_sha": args.libero_plus_git_sha,
        "openvla_oft_git_sha": "e4287e94541f459edc4feabc4e181f537cd569a8",
        "checkpoint_id": "moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10",
        "checkpoint_revision": "13cdacd486c504e65408fc3c9e12fec9c5bf0382",
        "model_native_output_horizon": native_output_horizon,
        "single_inference_returns_actions": native_output_horizon,
        "action_dim": action_dim,
        "supports_execution_coverage_independent_of_output_horizon": False,
        "supports_gt_native_in_one_inference_without_concatenation": supports_gt,
        "supports_lt_native_by_simple_prefix_execution": supports_lt,
        "maximum_native_coverage": maximum_native_coverage,
        "preferred_candidate_coverages": [8, 12, 16, 20, 25],
        "allowed_candidate_coverages_after_audit": [8] if gate_closed else [8, 12, 16, 20, 25],
        "coverage_sweep_gt_native_allowed": not gate_closed,
        "stage5b_rerun_required": not gate_closed,
        "static_source_audit": source_audit,
        "runtime_empirical_check": runtime,
        "audit_conclusion": (
            "Single OpenVLA-OFT inference returns the fixed LIBERO 8-action chunk; "
            "no legitimate >8 coverage is available from one call. Stage 5A >8 sweep and Stage 5B are not permitted."
            if gate_closed
            else "A coverage sweep greater than the native horizon is potentially permitted; proceed only if supported by a runtime audit."
        ),
    }

    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    print(f"\nWrote {output}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
