#!/usr/bin/env python3
"""Bypass the policy/postprocessor entirely and apply hand-crafted, known actions
directly to a fresh LIBERO env, to isolate whether the ~13x under-displacement seen
in diagnose_action_scale.py comes from our postprocessing/action-chunk pipeline or
from the env/controller path itself (env.step, use_delta toggle, physics substeps).

For each of several hand-crafted actions, applies it for `--repeat` consecutive
env.step() calls (from a fresh reset each time) and records the per-step and
cumulative end-effector displacement, so we can see both the single-step scale
and whether repeated identical commands accumulate roughly linearly.

Writes to <output-dir>/diagnostics/<suite>_tid<task_id>_s<seed>/raw_action_scale_check.json
"""

import argparse
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import make_libero_env
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json


def _eef_pos(obs):
    return [float(v) for v in obs["robot_state"]["eef"]["pos"]]


def _norm(vec):
    return float(sum(v * v for v in vec) ** 0.5)


def _run_case(cfg, suite, task_id, seed, action, repeat):
    import numpy as np

    env = make_libero_env(
        suite,
        task_id,
        seed=seed,
        control_mode=cfg.control_mode,
        obs_type=cfg.obs_type,
        camera_name=cfg.camera_name,
        observation_width=cfg.observation_width,
        observation_height=cfg.observation_height,
        init_states=cfg.init_states,
        episode_length=cfg.episode_length,
        num_steps_wait=cfg.num_steps_wait,
    )
    obs, _info = env.reset(seed=seed)
    start_pos = _eef_pos(obs)

    action_arr = np.asarray(action, dtype=np.float32)
    action_arr = np.clip(action_arr, env.action_space.low, env.action_space.high)

    steps = []
    prev_pos = start_pos
    for i in range(repeat):
        obs, _reward, terminated, truncated, _step_info = env.step(action_arr)
        pos = _eef_pos(obs)
        step_disp = [a - b for a, b in zip(pos, prev_pos)]
        steps.append(
            {
                "step": i,
                "eef_pos": pos,
                "step_displacement_m": step_disp,
                "step_displacement_norm_m": _norm(step_disp),
            }
        )
        prev_pos = pos
        if terminated or truncated:
            break

    total_disp = [a - b for a, b in zip(prev_pos, start_pos)]
    env.close()
    return {
        "applied_action": [float(v) for v in action_arr],
        "control_mode": cfg.control_mode,
        "start_eef_pos": start_pos,
        "steps": steps,
        "total_displacement_m": total_disp,
        "total_displacement_norm_m": _norm(total_disp),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--suite", default="libero_spatial")
    parser.add_argument("--task-id", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.output_dir:
        cfg.output_dir = args.output_dir

    episode_tag = f"{args.suite}_tid{args.task_id}_s{args.seed}"
    out_dir = ensure_dir(cfg.output_dir / "diagnostics" / episode_tag)

    # +X translation at max magnitude, no rotation, gripper closed (-1).
    case_max_x = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]
    # Half-magnitude +X translation, for a linearity check against case_max_x.
    case_half_x = [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]
    # -X translation at max magnitude, to check sign/direction consistency.
    case_neg_x = [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]

    results = {}
    for name, action in (
        ("max_x", case_max_x),
        ("half_x", case_half_x),
        ("neg_x", case_neg_x),
    ):
        print(f"running case {name}: action={action}")
        results[name] = _run_case(cfg, args.suite, args.task_id, args.seed, action, args.repeat)
        first_step_norm = results[name]["steps"][0]["step_displacement_norm_m"]
        total_norm = results[name]["total_displacement_norm_m"]
        print(f"  first_step_displacement_norm_m={first_step_norm:.4f}  total_norm_m={total_norm:.4f}")

    out = {
        "note": (
            "For an OSC_POSE controller with output_max=0.05m and input_max=1.0, "
            "a translation action of magnitude 1.0 should produce ~0.05m displacement "
            "per control step (allowing for some under-convergence toward the target "
            "within a single step, but not an order-of-magnitude shortfall). Bypasses "
            "the policy/postprocessor entirely -- if these hand-crafted actions also "
            "come back far under ~0.05m/step, the scale loss is in the env/controller "
            "path, not in our postprocessing or action-chunk handling."
        ),
        "cases": results,
    }
    write_json(out_dir / "raw_action_scale_check.json", out)
    print(f"wrote {out_dir / 'raw_action_scale_check.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
