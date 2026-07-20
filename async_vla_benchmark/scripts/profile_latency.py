#!/usr/bin/env python3
"""Profile native π0.5-LIBERO end-to-end request latency."""

import argparse
import math
import random
import statistics
from pathlib import Path

import numpy as np

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.environment import get_task_info, make_libero_env
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import ensure_dir, write_csv, write_json
from async_vla_benchmark.benchmark.metrics import percentile
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors, timed_request


def _collect_observations(env, instruction, policy, preprocessor, postprocessor, max_steps=50):
    """Run a short rollout and return a diverse list of observations."""
    obs_list = []
    obs, info = env.reset(seed=0)
    obs_list.append(obs)
    for _ in range(max_steps):
        _, processed, _ = timed_request(
            policy,
            preprocessor,
            postprocessor,
            obs,
            instruction,
            use_rtc=False,
        )
        action = np.clip(processed[0], env.action_space.low, env.action_space.high)
        obs, reward, terminated, truncated, info = env.step(action)
        obs_list.append(obs)
        if terminated or truncated:
            break
    return obs_list


def _measure(policy, preprocessor, postprocessor, obs_list, n):
    """Run `n` measured requests against sampled observations."""
    records = []
    for _ in range(n):
        obs = random.choice(obs_list)
        _, _, timing = timed_request(
            policy,
            preprocessor,
            postprocessor,
            obs,
            "",  # task instruction is not needed for raw latency; preprocessor will use obs task if present
            use_rtc=False,
        )
        records.append(timing)
    return records


def _summarize(records):
    values = [r["request_latency_ms"] for r in records]
    stats = {
        "mean_ms": statistics.mean(values),
        "std_ms": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min_ms": min(values),
        "max_ms": max(values),
        "p50_ms": percentile(values, 0.50),
        "p90_ms": percentile(values, 0.90),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
    }
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--warmup-requests", type=int, default=10)
    parser.add_argument("--measured-requests", type=int, default=100)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if not cfg.checkpoint_revision:
        raise ValueError("checkpoint_revision must be pinned before profiling")

    # Use the first candidate task for the profiling environment.
    candidate = cfg.task_candidates[0]
    task_id = candidate.task_ids[0]
    env = make_libero_env(
        candidate.suite,
        task_id,
        seed=0,
        control_mode=cfg.control_mode,
        obs_type=cfg.obs_type,
        camera_name=cfg.camera_name,
        observation_width=cfg.observation_width,
        observation_height=cfg.observation_height,
        init_states=cfg.init_states,
        episode_length=cfg.episode_length,
        num_steps_wait=cfg.num_steps_wait,
    )
    task_info = get_task_info(env, candidate.suite, task_id)

    policy = load_pi05_policy(
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
        n_action_steps=cfg.policy_n_action_steps,
        device=cfg.device,
    )
    preprocessor, postprocessor = load_pre_post_processors(
        policy,
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
    )

    obs_list = _collect_observations(env, task_info.language_instruction, policy, preprocessor, postprocessor)
    if len(obs_list) < 2:
        raise RuntimeError("could not collect enough observations for latency profiling")

    # Warm-up
    _measure(policy, preprocessor, postprocessor, obs_list, args.warmup_requests)
    # Measured
    records = _measure(policy, preprocessor, postprocessor, obs_list, args.measured_requests)

    summary = _summarize(records)
    summary["warmup_requests"] = args.warmup_requests
    summary["measured_requests"] = args.measured_requests
    summary["control_frequency_hz"] = 1.0 / (env.control_freq if hasattr(env, "control_freq") else 20.0)

    ensure_dir(cfg.output_dir / "summaries")
    ensure_dir(cfg.output_dir / "figures")

    csv_path = cfg.output_dir / "summaries" / "native_latency.csv"
    write_csv(csv_path, records)
    write_json(cfg.output_dir / "summaries" / "native_latency.json", summary)

    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(8, 5))
        plt.hist([r["request_latency_ms"] for r in records], bins=30, edgecolor="black")
        plt.xlabel("Request latency (ms)")
        plt.ylabel("Count")
        plt.title("Native π0.5-LIBERO request latency distribution")
        plt.savefig(cfg.output_dir / "figures" / "native_latency_distribution.png", dpi=150)
        plt.close()
    except Exception as exc:
        print(f"warning: could not generate histogram: {exc}")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
