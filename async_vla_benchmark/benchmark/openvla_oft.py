"""Pinned official OpenVLA-OFT adapter for the Stage 4 LIBERO diagnostic."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from .policy import _correct_libero_image_orientation, _libero_state_vector
from .stage4 import CHECKPOINT_ID, CHECKPOINT_REVISION, NATIVE_CHUNK_SIZE, OPENVLA_OFT_COMMIT

ACTION_HEAD_FILE = "action_head--300000_checkpoint.pt"
PROPRIO_PROJECTOR_FILE = "proprio_projector--300000_checkpoint.pt"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def resolve_unnorm_key(model: Any, suite: str) -> str:
    for key in (suite, f"{suite}_no_noops"):
        if key in model.norm_stats: return key
    raise ValueError(f"checkpoint contains no action unnormalization key for {suite}")


class OpenVLAOFTPolicy:
    """Thin wrapper around the pinned upstream evaluation utilities.

    The wrapper intentionally exposes only the official L1 action path. It does
    not accept RTC delay guidance and always returns the native 8x7 chunk.
    """

    def __init__(self, checkpoint_path: Path, repo_path: Path):
        try:
            from experiments.robot.libero.run_libero_eval import GenerateConfig, initialize_model
            from experiments.robot.openvla_utils import get_vla_action, resize_image_for_policy
        except ImportError as exc:
            raise RuntimeError("pinned OpenVLA-OFT checkout is not importable") from exc
        self.checkpoint_path = Path(checkpoint_path).resolve()
        self.repo_path = Path(repo_path).resolve()
        self.cfg = GenerateConfig(
            pretrained_checkpoint=str(self.checkpoint_path), use_l1_regression=True,
            use_diffusion=False, use_film=False, num_images_in_input=2,
            use_proprio=True, center_crop=True, num_open_loop_steps=8,
            load_in_8bit=False, load_in_4bit=False, use_wandb=False,
        )
        self.model, self.action_head, self.proprio_projector, noisy, self.processor = initialize_model(self.cfg)
        if noisy is not None: raise RuntimeError("Stage 4 prohibits a diffusion/noisy-action projector")
        self._get_vla_action = get_vla_action
        self._resize = resize_image_for_policy
        self.current_suite = None
        self.resolved_unnorm_key = None
        self.config = type("OpenVLAOFTConfig", (), {"chunk_size": 8})()

    def set_suite(self, suite: str) -> str:
        self.current_suite = suite
        self.resolved_unnorm_key = resolve_unnorm_key(self.model, suite)
        self.cfg.task_suite_name = suite
        self.cfg.unnorm_key = self.resolved_unnorm_key
        return self.resolved_unnorm_key

    def prepare_observation(self, observation: dict, task_instruction: str) -> dict:
        if self.resolved_unnorm_key is None: raise RuntimeError("set_suite must be called before inference")
        pixels = _correct_libero_image_orientation(observation["pixels"])
        by_lower = {key.lower(): value for key, value in pixels.items()}
        full = next((value for key, value in by_lower.items() if "agentview" in key), None)
        wrist = next((value for key, value in by_lower.items() if "eye_in_hand" in key or "wrist" in key), None)
        if full is None or wrist is None: raise ValueError(f"two-image path unavailable; pixel keys={sorted(pixels)}")
        return {
            "full_image": self._resize(np.asarray(full, dtype=np.uint8), 224),
            "wrist_image": self._resize(np.asarray(wrist, dtype=np.uint8), 224),
            "state": _libero_state_vector(observation),
            "task_description": task_instruction,
        }

    def predict_action_chunk(self, prepared: dict) -> np.ndarray:
        actions = np.asarray(self._get_vla_action(
            self.cfg, self.model, self.processor, prepared, prepared["task_description"],
            self.action_head, self.proprio_projector, None, use_film=False,
        ), dtype=np.float32)
        if actions.shape != (NATIVE_CHUNK_SIZE, 7): raise ValueError(f"OpenVLA-OFT returned {actions.shape}, expected (8, 7)")
        if not np.isfinite(actions).all(): raise ValueError("OpenVLA-OFT returned non-finite actions")
        return actions

    @staticmethod
    def postprocess(actions: Any) -> np.ndarray:
        from experiments.robot.robot_utils import invert_gripper_action, normalize_gripper_action
        array = np.asarray(actions, dtype=np.float32)
        return invert_gripper_action(normalize_gripper_action(array, binarize=True))

    def provenance(self) -> dict:
        action_head = self.checkpoint_path / ACTION_HEAD_FILE
        proprio = self.checkpoint_path / PROPRIO_PROJECTOR_FILE
        return {
            "policy_family": "openvla_oft", "checkpoint_id": CHECKPOINT_ID,
            "checkpoint_revision": CHECKPOINT_REVISION, "checkpoint_snapshot": str(self.checkpoint_path),
            "openvla_oft_git_sha": OPENVLA_OFT_COMMIT,
            "action_head_identity": ACTION_HEAD_FILE, "action_head_sha256": _sha256(action_head),
            "proprio_projector_identity": PROPRIO_PROJECTOR_FILE, "proprio_projector_sha256": _sha256(proprio),
            "processor_identity": type(self.processor).__module__ + "." + type(self.processor).__name__,
            "native_chunk_size": 8, "use_l1_regression": True, "use_diffusion": False,
            "use_film": False, "num_images_in_input": 2, "use_proprio": True,
            "center_crop": True, "load_in_8bit": False, "load_in_4bit": False,
        }


def verify_checkout(repo_path: Path) -> str:
    import subprocess
    sha = subprocess.run(["git", "-C", str(repo_path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if sha != OPENVLA_OFT_COMMIT: raise ValueError(f"wrong OpenVLA-OFT checkout: {sha}")
    return sha


def verify_snapshot(snapshot: Path) -> dict:
    required = ["config.json", "dataset_statistics.json", ACTION_HEAD_FILE, PROPRIO_PROJECTOR_FILE]
    missing = [name for name in required if not (snapshot / name).is_file()]
    if missing: raise ValueError(f"checkpoint snapshot missing {missing}")
    return {name: _sha256(snapshot / name) for name in required}


def write_policy_provenance(path: Path, policy: OpenVLAOFTPolicy, packages: dict) -> None:
    data = policy.provenance(); data["runtime_packages"] = packages
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
