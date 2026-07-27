#!/usr/bin/env python3
"""Dump raw observation structure, camera images, and orientation-conversion checks
for one LIBERO episode reset, to sanity-check the preprocessing pipeline against the
policy's expected inputs without running a full episode.

Writes to <output-dir>/diagnostics/<suite>_tid<task_id>_s<seed>/:
  - observation_structure.json   raw obs keys/shapes/dtypes, robot_state values
  - quat_axisangle_check.json    our _quat_to_axisangle vs robosuite's reference impl
  - preprocessed_batch.json      keys/shapes of the batch handed to policy.predict_action_chunk
  - <camera_name>.png            one frame per camera (if Pillow is available)
"""

import argparse
import json
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json
from async_vla_benchmark.benchmark.policy import (
    _libero_state_vector,
    _quat_to_axisangle,
    load_pi05_policy,
    load_pre_post_processors,
    preprocess_observation,
)


def _describe(value):
    import numpy as np

    if isinstance(value, dict):
        return {k: _describe(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        return {"shape": list(value.shape), "dtype": str(value.dtype)}
    try:
        import torch

        if isinstance(value, torch.Tensor):
            return {"shape": list(value.shape), "dtype": str(value.dtype), "device": str(value.device)}
    except ImportError:
        pass
    if isinstance(value, (list, tuple)):
        return [_describe(v) for v in value]
    return str(type(value))


def _save_images(observation, out_dir: Path) -> list[str]:
    saved = []
    pixels = observation.get("pixels")
    if not isinstance(pixels, dict):
        return saved
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed; skipping PNG export, describing shapes only")
        return saved
    for cam_name, image in pixels.items():
        arr = image
        try:
            import numpy as np

            arr = np.asarray(arr)
            if arr.dtype != np.uint8:
                arr = (arr * 255).clip(0, 255).astype(np.uint8) if arr.max() <= 1.0 else arr.astype(np.uint8)
            path = out_dir / f"{cam_name}.png"
            Image.fromarray(arr).save(path)
            saved.append(str(path))
        except Exception as exc:  # noqa: BLE001 - best-effort diagnostic, keep going
            print(f"failed to save image for {cam_name}: {exc}")
    return saved


def _check_quat_conversion(observation) -> dict:
    robot_state = observation["robot_state"]
    quat = robot_state["eef"]["quat"]
    ours = _quat_to_axisangle(quat)

    result = {
        "quat_xyzw": list(map(float, quat)),
        "our_axisangle": [float(v) for v in ours],
    }
    try:
        from robosuite.utils.transform_utils import quat2axisangle
        import numpy as np

        reference = quat2axisangle(np.array(quat, dtype=np.float64))
        result["robosuite_axisangle"] = [float(v) for v in reference]
        result["max_abs_diff"] = float(np.max(np.abs(np.array(ours, dtype=np.float64) - reference)))
        result["matches_robosuite"] = bool(result["max_abs_diff"] < 1e-6)
    except ImportError:
        result["robosuite_axisangle"] = None
        result["matches_robosuite"] = None
        result["note"] = "robosuite not importable; could not cross-check"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--suite", default="libero_spatial")
    parser.add_argument("--task-id", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if not cfg.checkpoint_revision:
        raise ValueError("checkpoint_revision must be pinned before diagnosis")

    episode_tag = f"{args.suite}_tid{args.task_id}_s{args.seed}"
    out_dir = ensure_dir(cfg.output_dir / "diagnostics" / episode_tag)

    env = make_libero_env(
        args.suite,
        args.task_id,
        seed=args.seed,
        control_mode=cfg.control_mode,
        obs_type=cfg.obs_type,
        camera_name=cfg.camera_name,
        observation_width=cfg.observation_width,
        observation_height=cfg.observation_height,
        init_states=cfg.init_states,
        episode_length=cfg.episode_length,
        num_steps_wait=cfg.num_steps_wait,
    )
    task_info = get_task_info(env, args.suite, args.task_id)
    obs, _info = env.reset(seed=args.seed)

    structure = {
        "task_name": task_info.task_name,
        "language_instruction": task_info.language_instruction,
        "control_mode": cfg.control_mode,
        "camera_name_config": cfg.camera_name,
        "action_space": {
            "low": env.action_space.low.tolist(),
            "high": env.action_space.high.tolist(),
        },
        "observation_keys": _describe(obs),
        "robot_state": {
            "eef_pos": [float(v) for v in obs["robot_state"]["eef"]["pos"]],
            "eef_quat_xyzw": [float(v) for v in obs["robot_state"]["eef"]["quat"]],
            "gripper_qpos": [float(v) for v in obs["robot_state"]["gripper"]["qpos"]],
            "state_vector_fed_to_policy": [float(v) for v in _libero_state_vector(obs)],
        },
    }
    write_json(out_dir / "observation_structure.json", structure)

    quat_check = _check_quat_conversion(obs)
    write_json(out_dir / "quat_axisangle_check.json", quat_check)

    image_paths = _save_images(obs, out_dir)

    policy = load_pi05_policy(
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
        n_action_steps=cfg.policy_n_action_steps,
        device=cfg.device,
    )
    preprocessor, _postprocessor = load_pre_post_processors(
        policy, cfg.policy_checkpoint, cfg.checkpoint_revision
    )
    batch = preprocess_observation(preprocessor, obs, task_info.language_instruction)

    input_features = None
    try:
        input_features = list(policy.config.input_features.keys())
    except AttributeError:
        pass

    write_json(
        out_dir / "preprocessed_batch.json",
        {
            "batch_keys_and_shapes": _describe(batch),
            "policy_expected_input_features": input_features,
        },
    )

    print(f"wrote diagnostics to {out_dir}")
    print(f"images saved: {image_paths}")
    print(f"quat check: {json.dumps(quat_check)}")
    print(f"policy expected input_features: {input_features}")
    print(f"batch keys: {list(batch.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
