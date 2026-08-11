#!/usr/bin/env python3
"""Stage 0 — run the 96-episode ID-only latency calibration.

    # 1. environment/policy assertions only, no episodes
    python -m async_vla_benchmark.scripts.run_stage0 --config ... --preflight-only

    # 2. the 36 Native episodes, as a viability smoke test
    python -m async_vla_benchmark.scripts.run_stage0 --config ... --native-only

    # 3. the full 96
    python -m async_vla_benchmark.scripts.run_stage0 --config ... --resume

Writes `latency_calibration_episode_results.csv` with exactly the columns
required by `docs/STAGE_0_LATENCY_CALIBRATION.md` section 7. Selection of `d*`
is a separate step (`select_high_delay.py`) so that producing the data and
choosing the operating point cannot be conflated.
"""

from __future__ import annotations

import argparse
import json
import math
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

from async_vla_benchmark.benchmark.config import BenchmarkConfig, load_config
from async_vla_benchmark.benchmark.environment import (
    get_max_episode_steps,
    get_task_info,
    make_libero_env,
)
from async_vla_benchmark.benchmark.execution import run_episode
from async_vla_benchmark.benchmark.latency import LatencyProfile
from async_vla_benchmark.benchmark.logging import ensure_dir, write_csv
from async_vla_benchmark.benchmark.metrics import percentile
from async_vla_benchmark.benchmark.policy import load_pi05_policy, load_pre_post_processors
from async_vla_benchmark.benchmark.rtc import build_rtc_config, configure_rtc
from async_vla_benchmark.benchmark.stage0 import (
    ADDED_DELAYS_MS,
    FIXED_HORIZON,
    REQUEST_THRESHOLD_ACTIONS,
    STAGE0_TASKS,
    TASKS_BY_KEY,
    Stage0Plan,
    stage0_manifest,
)

#: Exact section 7 column order. Written verbatim so the CSV can be diffed
#: against the spec rather than trusted.
RESULT_COLUMNS = [
    "run_id",
    "task_key",
    "task_group",
    "suite",
    "task_id",
    "task_name",
    "execution_method",
    "added_delay_ms",
    "seed",
    "success",
    "episode_steps",
    "completion_fraction",
    "request_latency_mean_ms",
    "request_latency_p50_ms",
    "request_latency_p95_ms",
    "action_age_mean_ms",
    "action_age_p50_ms",
    "action_age_p95_ms",
    "action_age_max_ms",
    "logical_delay_steps_mean",
    "logical_delay_steps_p95",
    "queue_occupancy_mean",
    "queue_occupancy_p95",
    "underrun_count",
    "hold_count",
    "discard_count",
    "num_policy_requests",
    "action_delta_mean",
    "action_accel_mean",
    "action_jerk_mean",
    "wall_clock_episode_s",
    "gpu_id",
    "status",
    "invalid_reason",
]


def _gpu_id() -> str:
    try:
        import torch

        if not torch.cuda.is_available():
            return "cpu"
        index = torch.cuda.current_device()
        return f"{index}:{torch.cuda.get_device_name(index)}"
    except Exception:  # noqa: BLE001 - identification must never fail a run
        return "unknown"


def _read_parquet_column(path: Path, column: str) -> list[float]:
    """Pull one column out of a per-episode artifact, or [] if unavailable.

    The episode summary carries means and p95s but not p50s or the per-request
    `delay_steps`, and section 7 requires both. Deriving them from the parquet
    the runner already writes keeps `execution.py` untouched.
    """
    if not path.exists():
        return []
    try:
        import pandas as pd

        frame = pd.read_parquet(path)
    except Exception:  # noqa: BLE001
        return []
    if column not in frame.columns:
        return []
    series = frame[column].dropna()
    return [float(v) for v in series.tolist()]


def _derived(output_dir: Path, run_id: str) -> dict[str, float]:
    requests = output_dir / "requests" / f"{run_id}.parquet"
    actions = output_dir / "actions" / f"{run_id}.parquet"

    latencies = _read_parquet_column(requests, "measured_request_latency_ms")
    delay_steps = _read_parquet_column(requests, "delay_steps")
    ages = _read_parquet_column(actions, "action_age_ms")
    depths = _read_parquet_column(actions, "queue_depth_before")

    def pct(values, p):
        return percentile(values, p) if values else math.nan

    def mean(values):
        return sum(values) / len(values) if values else math.nan

    return {
        "request_latency_p50_ms": pct(latencies, 0.50),
        "action_age_p50_ms": pct(ages, 0.50),
        "logical_delay_steps_mean": mean(delay_steps),
        "logical_delay_steps_p95": pct(delay_steps, 0.95),
        "queue_occupancy_p95": pct(depths, 0.95),
    }


def _row(
    plan: Stage0Plan,
    summary: dict[str, Any] | None,
    task_name: str,
    max_steps: int,
    output_dir: Path,
    gpu: str,
    status: str,
    invalid_reason: str,
) -> dict[str, Any]:
    base = {
        "run_id": plan.run_id,
        "task_key": plan.task_key,
        "task_group": plan.task_group,
        "suite": plan.suite,
        "task_id": plan.task_id,
        "task_name": task_name,
        "execution_method": plan.execution_method,
        "added_delay_ms": plan.added_delay_ms,
        "seed": plan.seed,
        "gpu_id": gpu,
        "status": status,
        "invalid_reason": invalid_reason,
    }
    if summary is None:
        return {**{column: "" for column in RESULT_COLUMNS}, **base}

    steps = summary["environment_steps"]
    base.update(
        {
            "success": int(bool(summary["success"])),
            "episode_steps": steps,
            # LIBERO exposes no subgoal signal, so there is no partial credit to
            # report. This is the fraction of the step budget consumed, which is
            # a timing diagnostic (early success -> small value), NOT task
            # progress. Do not read it as "how far it got" on failures.
            "completion_fraction": (steps / max_steps) if max_steps else math.nan,
            "request_latency_mean_ms": summary["mean_request_latency_ms"],
            "request_latency_p95_ms": summary["p95_request_latency_ms"],
            "action_age_mean_ms": summary["mean_action_age_ms"],
            "action_age_p95_ms": summary["p95_action_age_ms"],
            "action_age_max_ms": summary["maximum_action_age_ms"],
            "queue_occupancy_mean": summary["mean_queue_depth"],
            # Kept distinct per K010: a hold and a starved queue are different
            # failures that both inflate action age.
            "underrun_count": summary["queue_underrun_steps"],
            "hold_count": summary["hold_action_steps"],
            "discard_count": summary["discarded_old_actions"],
            "num_policy_requests": summary["number_of_policy_requests"],
            "action_delta_mean": summary["mean_action_delta_l2"],
            "action_accel_mean": summary["mean_action_acceleration_l2"],
            "action_jerk_mean": summary["mean_action_jerk_l2"],
            "wall_clock_episode_s": summary["wall_clock_runtime_seconds"],
        }
    )
    base.update(_derived(output_dir, plan.run_id))
    return {column: base.get(column, "") for column in RESULT_COLUMNS}


def _load_policy(cfg: BenchmarkConfig):
    policy = load_pi05_policy(
        cfg.policy_checkpoint,
        cfg.checkpoint_revision,
        n_action_steps=cfg.policy_n_action_steps,
        device=cfg.device,
    )
    # The checkpoint ships rtc_config=null, so without this LeRobot's
    # _rtc_enabled() is False and every per-request inference_delay /
    # execution_horizon argument is silently ignored -- the RTC arm would run as
    # plain naive async and nothing in the outputs would show it.
    if cfg.rtc.enabled:
        configure_rtc(
            policy,
            build_rtc_config(
                execution_horizon=FIXED_HORIZON,
                max_guidance_weight=cfg.rtc.max_guidance_weight,
                prefix_attention_schedule=cfg.rtc.prefix_attention_schedule,
            ),
        )
    preprocessor, postprocessor = load_pre_post_processors(
        policy, cfg.policy_checkpoint, cfg.checkpoint_revision
    )
    return policy, preprocessor, postprocessor


def preflight(cfg: BenchmarkConfig, check_policy: bool = True) -> int:
    """Assert every precondition Stage 0 depends on. Returns a process exit code.

    Each of these has silently invalidated a benchmark before: a task index that
    resolves to a different task than intended, a policy whose chunk length does
    not match the configured horizon, or an environment that exposes no control
    frequency (making the ms -> control-step conversion meaningless).
    """
    failures: list[str] = []

    from async_vla_benchmark.benchmark.environment import (
        require_lerobot_libero,
        resolve_control_frequency_hz,
    )

    require_lerobot_libero()
    from lerobot.envs.libero import _get_suite

    for task in STAGE0_TASKS:
        try:
            suite = _get_suite(task.suite)
            resolved = suite.get_task(task.task_id).name
            if resolved != task.expected_task_name:
                failures.append(
                    f"{task.suite}:{task.task_id} resolved to {resolved!r}, "
                    f"expected {task.expected_task_name!r}"
                )
            else:
                print(f"ok  {task.suite}:{task.task_id} -> {resolved}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{task.suite}:{task.task_id} lookup failed: {exc}")

    # One env is enough to read the control frequency; building all three here
    # would double preflight cost for no extra signal.
    probe = STAGE0_TASKS[0]
    try:
        env = make_libero_env(
            probe.suite,
            probe.task_id,
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
        hz = resolve_control_frequency_hz(env)
        print(f"ok  control frequency = {hz} Hz  (1 step = {1000.0 / hz:.2f} ms)")
        print(f"ok  max episode steps = {get_max_episode_steps(env)}")
        # Sanity-check the delay grid against the control period: a delay below
        # one control period rounds (ceil) to a single step, so several grid
        # points would be indistinguishable.
        period_ms = 1000.0 / hz
        if ADDED_DELAYS_MS[1] < period_ms:
            print(
                f"WARN +{ADDED_DELAYS_MS[1]} ms is under one control period "
                f"({period_ms:.1f} ms); low delay levels may collapse to the "
                "same number of logical steps"
            )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"environment construction failed: {exc}")

    if check_policy:
        try:
            policy, _, _ = _load_policy(cfg)
            steps = getattr(policy.config, "n_action_steps", None)
            if steps != FIXED_HORIZON:
                failures.append(
                    f"policy n_action_steps={steps}, expected {FIXED_HORIZON} (D002)"
                )
            else:
                print(f"ok  policy n_action_steps = {steps}")
            # RTC drops the leading `delay_steps` actions of each raw chunk, so it
            # can only fill the queue when `chunk_size - delay_steps >= H`. The
            # ADDED_DELAYS_MS cap keeps delay_steps <= H, which makes
            # `chunk_size >= 2 * H` the invariant the delay grid is derived from.
            # Assert it rather than trust it: if the checkpoint ever ships a
            # shorter chunk, the RTC arm silently starves and only the hold counts
            # would show it.
            chunk_size = getattr(policy.config, "chunk_size", None)
            if chunk_size is None:
                print(
                    "WARN policy.config.chunk_size unavailable; cannot verify the "
                    "RTC chunk budget (see stage0.ADDED_DELAYS_MS)"
                )
            elif chunk_size < 2 * FIXED_HORIZON:
                failures.append(
                    f"policy chunk_size={chunk_size}, need >= {2 * FIXED_HORIZON} "
                    f"so RTC can still fill a {FIXED_HORIZON}-action queue after "
                    "discarding the delay prefix"
                )
            else:
                print(f"ok  policy chunk_size = {chunk_size} (>= 2 x {FIXED_HORIZON})")
            rtc_cfg = getattr(policy.config, "rtc_config", None)
            if cfg.rtc.enabled and rtc_cfg is None:
                failures.append("rtc.enabled is true but policy.config.rtc_config is None")
            else:
                print("ok  RTC config attached to policy")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"policy load failed: {exc}")

    if failures:
        print("\nPREFLIGHT FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nPREFLIGHT PASSED")
    return 0


def run(cfg: BenchmarkConfig, plans: list[Stage0Plan], args) -> int:
    output_dir = Path(cfg.output_dir)
    for sub in ("requests", "actions", "episodes", "summaries"):
        ensure_dir(output_dir / sub)

    gpu = _gpu_id()
    policy = preprocessor = postprocessor = None
    env_cache: dict[str, Any] = {}
    task_names: dict[str, str] = {}
    max_steps_by_task: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    failures = 0

    for index, plan in enumerate(plans, 1):
        episode_json = output_dir / "episodes" / f"{plan.run_id}.json"
        prefix = f"[{index}/{len(plans)}] {plan.run_id}"

        summary = None
        status, invalid_reason = "ok", ""

        if args.resume and episode_json.exists():
            summary = json.loads(episode_json.read_text())
            print(f"{prefix}: reused (success={summary['success']})")

        if summary is None:
            try:
                env_key = f"{plan.suite}:{plan.task_id}"
                if env_key not in env_cache:
                    env_cache[env_key] = make_libero_env(
                        plan.suite,
                        plan.task_id,
                        seed=plan.seed,
                        control_mode=cfg.control_mode,
                        obs_type=cfg.obs_type,
                        camera_name=cfg.camera_name,
                        observation_width=cfg.observation_width,
                        observation_height=cfg.observation_height,
                        init_states=cfg.init_states,
                        episode_length=cfg.episode_length,
                        num_steps_wait=cfg.num_steps_wait,
                    )
                env = env_cache[env_key]

                if plan.task_key not in task_names:
                    info = get_task_info(env, plan.suite, plan.task_id)
                    task_names[plan.task_key] = info.task_name
                    max_steps_by_task[plan.task_key] = get_max_episode_steps(env)
                    expected = TASKS_BY_KEY[plan.task_key].expected_task_name
                    if info.task_name != expected:
                        raise RuntimeError(
                            f"task name mismatch: env reports {info.task_name!r}, "
                            f"spec expects {expected!r}"
                        )

                if policy is None:
                    policy, preprocessor, postprocessor = _load_policy(cfg)

                # Scope RTC guidance to the RTC arm only. Without this the naive
                # arm shares a policy object that has rtc_config attached, and a
                # contaminated control arm would be invisible in the outputs.
                if cfg.rtc.enabled:
                    policy.config.rtc_config.enabled = plan.execution_method == "rtc"

                profile_cfg = next(
                    (p for p in cfg.latency_profiles if p.name == plan.latency_profile),
                    None,
                )
                if profile_cfg is None:
                    raise RuntimeError(
                        f"latency profile {plan.latency_profile!r} missing from config"
                    )
                if profile_cfg.added_latency_ms != plan.added_delay_ms:
                    raise RuntimeError(
                        f"profile {plan.latency_profile!r} has "
                        f"added_latency_ms={profile_cfg.added_latency_ms}, "
                        f"manifest expects {plan.added_delay_ms}"
                    )

                info = get_task_info(env, plan.suite, plan.task_id)
                summary = run_episode(
                    env=env,
                    policy=policy,
                    preprocessor=preprocessor,
                    postprocessor=postprocessor,
                    task_instruction=info.language_instruction,
                    episode_id=plan.run_id,
                    strategy=plan.execution_method,
                    latency_profile=LatencyProfile(
                        profile_cfg.name,
                        profile_cfg.use_measured_native_latency,
                        profile_cfg.added_latency_ms,
                    ),
                    fixed_horizon=FIXED_HORIZON,
                    output_dir=output_dir,
                    seed=plan.seed,
                    use_rtc=(plan.execution_method == "rtc"),
                    rtc_execution_horizon=FIXED_HORIZON,
                    request_threshold_actions=REQUEST_THRESHOLD_ACTIONS,
                    device=cfg.device,
                )
                print(
                    f"{prefix}: success={summary['success']} "
                    f"steps={summary['environment_steps']} "
                    f"age_p95={summary['p95_action_age_ms']:.0f}ms"
                )
            except Exception as exc:  # noqa: BLE001
                # One bad episode must not cost the other 95. Record it as
                # invalid and continue; section 12 requires invalid-cell
                # accounting anyway, and a silent gap is worse than a logged one.
                failures += 1
                status = "invalid"
                invalid_reason = f"{type(exc).__name__}: {exc}"
                print(f"{prefix}: FAILED {invalid_reason}")
                if args.verbose:
                    traceback.print_exc()

        rows.append(
            _row(
                plan=plan,
                summary=summary,
                task_name=task_names.get(plan.task_key, ""),
                max_steps=max_steps_by_task.get(plan.task_key, 0),
                output_dir=output_dir,
                gpu=gpu,
                status=status,
                invalid_reason=invalid_reason,
            )
        )

    results_path = output_dir / "latency_calibration_episode_results.csv"
    _merge_and_write(results_path, rows)
    print(f"\nwrote {results_path} ({len(rows)} rows this run, {failures} invalid)")
    return 1 if failures else 0


def _merge_and_write(path: Path, rows: list[dict[str, Any]]) -> None:
    """Merge into any existing CSV, keyed by run_id.

    A filtered run (--native-only, --task, --method) only produces its own
    subset; a plain overwrite would drop every episode outside the filter and
    the selection step would then silently calibrate on a fraction of the data.
    """
    from async_vla_benchmark.benchmark.logging import read_csv

    merged: dict[str, dict[str, Any]] = {}
    if path.exists():
        for existing in read_csv(path):
            merged[existing["run_id"]] = existing
    for row in rows:
        merged[row["run_id"]] = row
    ordered = sorted(merged.values(), key=lambda r: str(r["run_id"]))
    write_csv(path, [{c: r.get(c, "") for c in RESULT_COLUMNS} for r in ordered])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="run task/policy/environment assertions and exit",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="skip assertions (only for reruns of an already-verified setup)",
    )
    parser.add_argument(
        "--native-only",
        action="store_true",
        help="run only the 36 Native (0 ms) episodes as a viability smoke test",
    )
    parser.add_argument("--task", action="append", help="task_key filter, repeatable")
    parser.add_argument("--method", action="append", help="execution method filter")
    parser.add_argument("--delay", type=int, action="append", help="added delay filter")
    parser.add_argument("--seed", type=int, action="append", help="seed filter")
    parser.add_argument("--resume", action="store_true", help="skip completed episodes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.output_dir:
        cfg.output_dir = args.output_dir

    plans = stage0_manifest()
    if args.native_only:
        plans = [p for p in plans if p.added_delay_ms == 0]
    if args.task:
        plans = [p for p in plans if p.task_key in set(args.task)]
    if args.method:
        plans = [p for p in plans if p.execution_method in set(args.method)]
    if args.delay:
        plans = [p for p in plans if p.added_delay_ms in set(args.delay)]
    if args.seed:
        plans = [p for p in plans if p.seed in set(args.seed)]

    if args.dry_run:
        for index, plan in enumerate(plans, 1):
            print(index, asdict(plan))
        print(f"planned_episodes={len(plans)}")
        return 0

    if not args.skip_preflight:
        code = preflight(cfg)
        if code != 0:
            return code
    if args.preflight_only:
        return 0

    if not plans:
        print("no episodes selected after filtering")
        return 1
    return run(cfg, plans, args)


if __name__ == "__main__":
    raise SystemExit(main())
