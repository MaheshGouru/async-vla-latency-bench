#!/usr/bin/env python3
"""Check whether the policy's output-side action un-normalization and the LIBERO
controller's delta-action scale actually agree, by (1) dumping any discoverable
normalization stats on the pre/post processors, (2) comparing a raw model output
to its postprocessed value, and (3) applying that action for one real env.step and
measuring the actual physical displacement it produced.

A delta action of magnitude 1.0 on a robosuite OSC_POSE controller nominally moves
the end effector by the controller's configured `output_max` (commonly ~0.05m
position / ~0.5rad orientation per control step, though this is configurable and
not guaranteed to match what a given checkpoint was trained against). If the
measured displacement for a given action magnitude is wildly off from that
ballpark, the action scale is the more likely explanation for near-zero task
success than a plumbing bug.

Writes to <output-dir>/diagnostics/<suite>_tid<task_id>_s<seed>/action_scale_check.json
"""

import argparse
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json
from async_vla_benchmark.benchmark.policy import (
    load_pi05_policy,
    load_pre_post_processors,
    preprocess_observation,
)


def _describe_array(name, arr):
    import numpy as np

    arr = np.asarray(arr, dtype=np.float64)
    return {
        "name": name,
        "shape": list(arr.shape),
        "min": arr.min(axis=0).tolist() if arr.ndim > 1 else float(arr.min()),
        "max": arr.max(axis=0).tolist() if arr.ndim > 1 else float(arr.max()),
        "mean": arr.mean(axis=0).tolist() if arr.ndim > 1 else float(arr.mean()),
    }


def _find_controller_config(env) -> dict:
    """Best-effort walk to the robosuite OSC_POSE controller's gain/scale config."""
    candidates = []
    obj = env
    for _ in range(6):
        unwrapped = getattr(obj, "unwrapped", None)
        if unwrapped is not None and unwrapped is not obj:
            obj = unwrapped
        robots = getattr(obj, "robots", None)
        if robots:
            for robot in robots:
                controller = getattr(robot, "controller", None)
                if controller is not None:
                    candidates.append(controller)
            break
        env_attr = getattr(obj, "env", None)
        if env_attr is None:
            # LeRobot's LiberoEnv stores the underlying robosuite/LIBERO
            # OffScreenRenderEnv as `_env`, not `env` or `unwrapped`.
            env_attr = getattr(obj, "_env", None)
        if env_attr is None or env_attr is obj:
            break
        obj = env_attr

    for controller in candidates:
        info = {"controller_class": type(controller).__name__}
        for attr in ("output_max", "output_min", "input_max", "input_min", "kp", "kv", "control_dim"):
            value = getattr(controller, attr, None)
            if value is not None:
                try:
                    import numpy as np

                    info[attr] = np.asarray(value).tolist()
                except Exception:  # noqa: BLE001
                    info[attr] = str(value)
        if len(info) > 1:
            return info
    return {"note": "could not locate a robosuite controller object on the env"}


def _find_normalization_stats(processor) -> dict:
    """Best-effort reflection over the pre/post processor pipeline for any
    normalization stats (mean/std/min/max) attached to its steps."""
    import numpy as np

    findings = []
    steps = getattr(processor, "steps", None) or getattr(processor, "pipeline", None) or [processor]
    for step in steps:
        step_info = {"class": type(step).__name__}
        for attr_name in dir(step):
            if attr_name.startswith("_"):
                continue
            try:
                value = getattr(step, attr_name)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(value, dict):
                for key, sub in value.items():
                    if hasattr(sub, "shape") or isinstance(sub, (list, tuple)):
                        try:
                            arr = np.asarray(sub, dtype=np.float64)
                            if arr.size and arr.size < 64:
                                step_info[f"{attr_name}.{key}"] = arr.tolist()
                        except Exception:  # noqa: BLE001
                            pass
            elif hasattr(value, "shape"):
                try:
                    arr = np.asarray(value, dtype=np.float64)
                    if arr.size and arr.size < 64:
                        step_info[attr_name] = arr.tolist()
                except Exception:  # noqa: BLE001
                    pass
        if len(step_info) > 1:
            findings.append(step_info)
    return {"steps": findings} if findings else {"note": "no numeric stats attributes discovered via reflection"}


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

    controller_config = _find_controller_config(env)

    policy = load_pi05_policy(
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
        n_action_steps=cfg.policy_n_action_steps,
        device=cfg.device,
    )
    preprocessor, postprocessor = load_pre_post_processors(
        policy, cfg.policy_checkpoint, cfg.checkpoint_revision
    )

    import torch

    batch = preprocess_observation(preprocessor, obs, task_info.language_instruction)
    with torch.no_grad():
        raw_chunk = policy.predict_action_chunk(batch)
    processed_chunk = postprocessor(raw_chunk)
    if hasattr(processed_chunk, "action"):
        processed_chunk = processed_chunk.action
    if hasattr(processed_chunk, "numpy"):
        processed_chunk = processed_chunk.numpy(force=True)
    if processed_chunk.ndim == 3 and processed_chunk.shape[0] == 1:
        processed_chunk = processed_chunk[0]
    raw_np = raw_chunk if not hasattr(raw_chunk, "numpy") else raw_chunk.numpy(force=True)
    if raw_np.ndim == 3 and raw_np.shape[0] == 1:
        raw_np = raw_np[0]

    normalization_stats = _find_normalization_stats(postprocessor)

    eef_pos_before = [float(v) for v in obs["robot_state"]["eef"]["pos"]]
    gripper_before = [float(v) for v in obs["robot_state"]["gripper"]["qpos"]]

    import numpy as np

    first_action = np.clip(processed_chunk[0], env.action_space.low, env.action_space.high)
    obs_after, _reward, _term, _trunc, _step_info = env.step(first_action)
    eef_pos_after = [float(v) for v in obs_after["robot_state"]["eef"]["pos"]]
    displacement = [a - b for a, b in zip(eef_pos_after, eef_pos_before)]
    displacement_norm = float(sum(d * d for d in displacement) ** 0.5)

    result = {
        "task_name": task_info.task_name,
        "control_mode": cfg.control_mode,
        "action_space_bounds": {
            "low": env.action_space.low.tolist(),
            "high": env.action_space.high.tolist(),
        },
        "controller_config": controller_config,
        "normalization_stats_found": normalization_stats,
        "raw_model_output_chunk": _describe_array("raw_chunk", raw_np),
        "postprocessed_action_chunk": _describe_array("processed_chunk", processed_chunk),
        "applied_first_action": [float(v) for v in first_action],
        "eef_pos_before": eef_pos_before,
        "eef_pos_after": eef_pos_after,
        "gripper_qpos_before": gripper_before,
        "measured_translation_displacement_m": displacement,
        "measured_translation_displacement_norm_m": displacement_norm,
        "requested_translation_action_norm": float(
            sum(v * v for v in first_action[:3]) ** 0.5
        ),
        "note": (
            "For a well-calibrated robosuite OSC_POSE delta controller, a translation "
            "action of unit norm 1.0 nominally corresponds to roughly 0.05m of "
            "displacement per control step (robosuite's common default output_max). "
            "Compare measured_translation_displacement_norm_m against "
            "requested_translation_action_norm * ~0.05 as a rough sanity check; a "
            "large mismatch (order-of-magnitude over/under) suggests an action-scale "
            "mismatch between this env's controller config and what the checkpoint "
            "was trained against, rather than a preprocessing bug."
        ),
    }
    write_json(out_dir / "action_scale_check.json", result)

    print(f"wrote {out_dir / 'action_scale_check.json'}")
    print(f"controller_config: {controller_config}")
    print(f"normalization_stats_found: {normalization_stats}")
    print(f"requested_translation_action_norm: {result['requested_translation_action_norm']:.4f}")
    print(f"measured_translation_displacement_norm_m: {displacement_norm:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
