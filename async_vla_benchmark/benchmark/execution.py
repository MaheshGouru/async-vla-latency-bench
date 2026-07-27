"""Dependency-free discrete-event execution state and provenance."""

import time
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from .environment import get_max_episode_steps, resolve_control_frequency_hz
from .latency import LatencyProfile, request_delay_steps
from .metrics import mean_continuity, percentile
from .policy import timed_request
from .queues import ActionQueue, QueuedAction


@dataclass(frozen=True)
class ObservationRef:
    observation_id: str
    control_step: int
    logical_time_seconds: float


@dataclass(frozen=True)
class ChunkRef:
    chunk_id: str
    source_observation_id: str
    request_step: int
    request_logical_time: float
    response_available_step: int
    measured_request_latency_ms: float
    added_latency_ms: float
    delay_steps: int


def action_age_steps(execution_control_step: int, source_observation_step: int) -> int:
    age = execution_control_step - source_observation_step
    if age < 0:
        raise ValueError("action age cannot be negative")
    return age


def action_age_ms(age_steps: int, control_period_seconds: float) -> float:
    if age_steps < 0:
        raise ValueError("action age cannot be negative")
    if control_period_seconds <= 0:
        raise ValueError("control period must be positive")
    return round(age_steps * control_period_seconds * 1000.0, 6)


def make_hold_action(last_gripper_command: float, action_dimension: int = 7) -> list[float]:
    if action_dimension != 7:
        raise ValueError("the specified LIBERO hold action requires a 7D relative action")
    return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, float(last_gripper_command)]


@dataclass
class PendingRequest:
    request_id: str
    available_step: int
    payload: Any


class EventClock:
    """Logical clock; it deliberately contains no sleeping or wall-time pacing."""

    def __init__(self, control_period_seconds: float):
        if control_period_seconds <= 0:
            raise ValueError("control period must be positive")
        self.control_period_seconds = control_period_seconds
        self.control_step = 0
        self.pending: Optional[PendingRequest] = None

    @property
    def logical_time_seconds(self) -> float:
        return self.control_step * self.control_period_seconds

    def submit(self, request: PendingRequest) -> None:
        if self.pending is not None:
            raise RuntimeError("only one policy request may be outstanding")
        if request.available_step < self.control_step:
            raise ValueError("response availability cannot be in the past")
        self.pending = request

    def take_available(self) -> Optional[PendingRequest]:
        if self.pending is not None and self.control_step >= self.pending.available_step:
            result, self.pending = self.pending, None
            return result
        return None

    def advance(self) -> None:
        self.control_step += 1


class EpisodeRunner:
    """Run a single LIBERO episode under a given latency strategy."""

    def __init__(
        self,
        env: Any,
        policy: Any,
        preprocessor: Any,
        postprocessor: Any,
        task_instruction: str,
        strategy: str,
        latency_profile: LatencyProfile,
        fixed_horizon: int,
        episode_id: str,
        output_dir: Any,
        *,
        use_rtc: bool = False,
        rtc_execution_horizon: int = 10,
        request_threshold_actions: Optional[int] = None,
        max_steps: Optional[int] = None,
        device: str = "cuda",
    ) -> None:
        self.env = env
        self.policy = policy
        self.preprocessor = preprocessor
        self.postprocessor = postprocessor
        self.task_instruction = task_instruction
        self.strategy = strategy
        self.latency_profile = latency_profile
        self.fixed_horizon = fixed_horizon
        self.use_rtc = use_rtc
        self.rtc_execution_horizon = rtc_execution_horizon
        self.episode_id = episode_id
        self.output_dir = output_dir
        self.device = device
        self.control_frequency_hz = resolve_control_frequency_hz(env)
        self.control_period_seconds = 1.0 / self.control_frequency_hz
        self.clock = EventClock(self.control_period_seconds)
        self.queue = ActionQueue(fixed_horizon, request_threshold=request_threshold_actions)
        self.max_steps = max_steps if max_steps is not None else get_max_episode_steps(env)

        self.observations: list[ObservationRef] = []
        self.requests: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []

        self._request_counter = 0
        self._chunk_counter = 0
        self._observation_counter = 1  # source observations are 1-indexed per step
        self._last_gripper = 1.0  # safe open-ish default; updated by executed actions
        self._episode_start_wall = time.perf_counter()
        self._total_model_inference_ms = 0.0
        self._wall_clock_runtime_seconds = 0.0
        self._success = False

    def _new_observation_id(self) -> str:
        obs_id = f"{self.episode_id}_obs{self._observation_counter}"
        self._observation_counter += 1
        return obs_id

    def _new_chunk_id(self) -> str:
        chunk_id = f"{self.episode_id}_chunk{self._chunk_counter}"
        self._chunk_counter += 1
        return chunk_id

    def _new_request_id(self) -> str:
        req_id = f"{self.episode_id}_req{self._request_counter}"
        self._request_counter += 1
        return req_id

    def _record_observation(self, control_step: int) -> ObservationRef:
        obs_id = self._new_observation_id()
        ref = ObservationRef(
            observation_id=obs_id,
            control_step=control_step,
            logical_time_seconds=control_step * self.control_period_seconds,
        )
        self.observations.append(ref)
        return ref

    def _start_request(self, obs: Any, source_obs: ObservationRef, prev_raw_remainder: Optional[np.ndarray] = None) -> PendingRequest:
        """Run the policy synchronously and schedule a logically-delayed response."""
        request_id = self._new_request_id()
        self.queue.begin_request(request_id)

        execution_horizon = self.rtc_execution_horizon if self.use_rtc else None
        raw_chunk, processed_chunk, timing = timed_request(
            self.policy,
            self.preprocessor,
            self.postprocessor,
            obs,
            self.task_instruction,
            delay_steps=0,  # delay is simulated after measurement
            previous_chunk_remainder=prev_raw_remainder,
            execution_horizon=execution_horizon,
            use_rtc=self.use_rtc,
        )

        delay_steps = request_delay_steps(
            self.latency_profile,
            timing["request_latency_ms"],
            self.control_period_seconds,
        )
        available_step = source_obs.control_step + delay_steps

        # For RTC, discard the first `delay_steps` actions (they correspond to the hold
        # period and were already guided by the previous chunk). For all other strategies,
        # execute the returned chunk starting from its first action.
        if self.use_rtc and delay_steps > 0:
            start = min(delay_steps, raw_chunk.shape[0])
            raw_chunk = raw_chunk[start:]
            processed_chunk = processed_chunk[start:]

        chunk_id = self._new_chunk_id()
        chunk_ref = ChunkRef(
            chunk_id=chunk_id,
            source_observation_id=source_obs.observation_id,
            request_step=source_obs.control_step,
            request_logical_time=source_obs.logical_time_seconds,
            response_available_step=available_step,
            measured_request_latency_ms=timing["request_latency_ms"],
            added_latency_ms=self.latency_profile.added_latency_ms,
            delay_steps=delay_steps,
        )

        queued = self._to_queued_actions(processed_chunk, raw_chunk, chunk_ref)
        self.requests.append(
            {
                "request_id": request_id,
                "chunk_id": chunk_id,
                "source_observation_id": source_obs.observation_id,
                "source_observation_step": source_obs.control_step,
                "request_step": source_obs.control_step,
                "request_logical_time_seconds": source_obs.logical_time_seconds,
                "response_available_step": available_step,
                "measured_request_latency_ms": timing["request_latency_ms"],
                "model_latency_ms": timing["model_latency_ms"],
                "preprocessing_latency_ms": timing["preprocessing_latency_ms"],
                "postprocessing_latency_ms": timing["postprocessing_latency_ms"],
                "added_latency_ms": self.latency_profile.added_latency_ms,
                "delay_steps": delay_steps,
                "strategy": self.strategy,
                "latency_profile": self.latency_profile.name,
                "fixed_horizon": self.fixed_horizon,
            }
        )
        self._total_model_inference_ms += timing["model_latency_ms"]
        return PendingRequest(request_id, available_step, (queued, chunk_ref, timing))

    def _to_queued_actions(
        self,
        processed_chunk: np.ndarray,
        raw_chunk: np.ndarray,
        chunk_ref: ChunkRef,
    ) -> list[QueuedAction]:
        actions = []
        for i in range(min(self.fixed_horizon, processed_chunk.shape[0])):
            actions.append(
                QueuedAction(
                    value=processed_chunk[i],
                    raw_value=raw_chunk[i] if i < raw_chunk.shape[0] else None,
                    chunk_id=chunk_ref.chunk_id,
                    chunk_action_index=i,
                    source_observation_id=chunk_ref.source_observation_id,
                    source_observation_step=chunk_ref.request_step,
                )
            )
        return actions

    def _take_available(self) -> Optional[ChunkRef]:
        pending = self.clock.take_available()
        if pending is None:
            return None
        queued, chunk_ref, _ = pending.payload
        self.queue.replace(pending.request_id, queued)
        return chunk_ref

    def _maybe_request(self, obs: Any, source_obs: ObservationRef) -> Optional[PendingRequest]:
        """Start a new request if the strategy and queue state allow it."""
        if self.clock.pending is not None:
            return None
        if self.strategy in ("ideal_sync", "blocking_sync"):
            if len(self.queue) > 0:
                return None
        elif self.strategy in ("naive_async", "rtc"):
            if not self.queue.should_request():
                return None
        else:
            raise ValueError(f"unknown strategy {self.strategy}")

        prev_raw = None
        if self.use_rtc:
            prev_raw = np.stack([a.raw_value for a in self.queue.remainder() if a.raw_value is not None]) if self.queue.remainder() else None
            if prev_raw is not None and prev_raw.ndim == 1:
                prev_raw = prev_raw.reshape(1, -1)

        return self._start_request(obs, source_obs, prev_raw)

    def _select_action(self, control_step: int) -> tuple[np.ndarray, dict[str, Any]]:
        queue_depth_before = len(self.queue)
        queued = self.queue.pop()
        queue_depth_after = len(self.queue)
        is_hold = queued is None
        is_underrun = is_hold and self.strategy in ("blocking_sync", "naive_async", "rtc")
        if is_hold:
            action = np.array(make_hold_action(self._last_gripper), dtype=np.float32)
            chunk_id = None
            chunk_action_index = None
            source_obs_id = None
            source_obs_step = None
        else:
            action = queued.value
            if len(action) >= 7:
                self._last_gripper = float(action[6])
            chunk_id = queued.chunk_id
            chunk_action_index = queued.chunk_action_index
            source_obs_id = queued.source_observation_id
            source_obs_step = queued.source_observation_step
        return action, {
            "is_hold_action": is_hold,
            "is_queue_underrun": is_underrun,
            "queue_depth_before": queue_depth_before,
            "queue_depth_after": queue_depth_after,
            "chunk_id": chunk_id,
            "chunk_action_index": chunk_action_index,
            "source_observation_id": source_obs_id,
            "source_observation_step": source_obs_step,
        }

    def _clip_action(self, action: np.ndarray) -> np.ndarray:
        low = self.env.action_space.low
        high = self.env.action_space.high
        return np.clip(action, low, high)

    def _record_action(
        self,
        control_step: int,
        action: np.ndarray,
        meta: dict[str, Any],
        info: dict[str, Any],
    ) -> None:
        source_step = meta.get("source_observation_step")
        if source_step is None:
            age_steps = 0
            age_ms = 0.0
        else:
            age_steps = action_age_steps(control_step, source_step)
            age_ms = action_age_ms(age_steps, self.control_period_seconds)
        self.actions.append(
            {
                "episode_id": self.episode_id,
                "control_step": control_step,
                "logical_time_seconds": control_step * self.control_period_seconds,
                "strategy": self.strategy,
                "latency_profile": self.latency_profile.name,
                "fixed_horizon": self.fixed_horizon,
                "chunk_id": meta.get("chunk_id"),
                "chunk_action_index": meta.get("chunk_action_index"),
                "source_observation_id": meta.get("source_observation_id"),
                "source_observation_step": source_step,
                "action_age_steps": age_steps,
                "action_age_ms": age_ms,
                "queue_depth_before": meta["queue_depth_before"],
                "queue_depth_after": meta["queue_depth_after"],
                "is_hold_action": meta["is_hold_action"],
                "is_queue_underrun": meta["is_queue_underrun"],
                "is_success": bool(info.get("is_success", False)),
                "action_vector": action.tolist(),
            }
        )

    def run(self, seed: int) -> dict[str, Any]:
        obs, info = self.env.reset(seed=seed)
        done = False
        success = False
        control_step = 1
        self.clock.control_step = control_step

        # Seed the naive/RTC queues with an ideal-startup chunk.
        if self.strategy in ("naive_async", "rtc"):
            startup_profile = LatencyProfile("ideal", False, 0.0)
            old_profile = self.latency_profile
            self.latency_profile = startup_profile
            startup_obs = self._record_observation(control_step)
            startup_request = self._start_request(obs, startup_obs, None)
            self.clock.submit(startup_request)
            self._take_available()
            self.latency_profile = old_profile

        while not done and control_step <= self.max_steps:
            # 1. Make any newly available response actionable.
            if self.clock.pending is not None and self.clock.control_step >= self.clock.pending.available_step:
                self._take_available()

            # 2. Capture the current observation (only if we need it for a request this step).
            source_obs = None
            if self.strategy in ("naive_async", "rtc"):
                if self.queue.should_request():
                    source_obs = self._record_observation(control_step)
            else:
                if len(self.queue) == 1 and self.clock.pending is None:
                    # For ideal/blocking, request as soon as the queue is empty *after* this pop.
                    pass
                if len(self.queue) == 0 and self.clock.pending is None:
                    source_obs = self._record_observation(control_step)

            if source_obs is not None:
                request = self._maybe_request(obs, source_obs)
                if request is not None:
                    self.clock.submit(request)
                    # Ideal responses are immediately available.
                    if self.latency_profile.name == "ideal":
                        self._take_available()

            # 3. Select and execute the action for this control step.
            action, meta = self._select_action(control_step)
            action_clipped = self._clip_action(action)
            obs, reward, terminated, truncated, info = self.env.step(action_clipped)
            done = terminated or truncated or bool(info.get("is_success", False))
            if done and info.get("is_success"):
                success = True

            self._record_action(control_step, action_clipped, meta, info)

            # 4. Advance logical time.
            control_step += 1
            self.clock.advance()

        self._success = success
        self._wall_clock_runtime_seconds = time.perf_counter() - self._episode_start_wall
        self._write_outputs()
        return self._summarize(self._success, len(self.actions))

    def _summarize(self, success: bool, environment_steps: int) -> dict[str, Any]:
        import statistics

        request_latencies = [r["measured_request_latency_ms"] for r in self.requests]
        action_ages = [a["action_age_ms"] for a in self.actions]
        queue_depths = [a["queue_depth_before"] for a in self.actions]
        deltas = [np.linalg.norm(np.array(a["action_vector"][:6])) for a in self.actions]

        def pct(values, p):
            return percentile(values, p) if values else float("nan")

        summary = {
            "episode_id": self.episode_id,
            "strategy": self.strategy,
            "latency_profile": self.latency_profile.name,
            "fixed_horizon": self.fixed_horizon,
            "success": success,
            "environment_steps": environment_steps,
            "logical_completion_time_seconds": environment_steps * self.control_period_seconds,
            "wall_clock_runtime_seconds": self._wall_clock_runtime_seconds,
            "number_of_policy_requests": len(self.requests),
            "total_model_inference_ms": self._total_model_inference_ms,
            "mean_request_latency_ms": statistics.mean(request_latencies) if request_latencies else float("nan"),
            "p95_request_latency_ms": pct(request_latencies, 0.95),
            "mean_action_age_ms": statistics.mean(action_ages) if action_ages else float("nan"),
            "p95_action_age_ms": pct(action_ages, 0.95),
            "maximum_action_age_ms": max(action_ages) if action_ages else float("nan"),
            "mean_queue_depth": statistics.mean(queue_depths) if queue_depths else float("nan"),
            "minimum_queue_depth": min(queue_depths) if queue_depths else float("nan"),
            "queue_underrun_steps": sum(1 for a in self.actions if a["is_queue_underrun"]),
            "hold_action_steps": sum(1 for a in self.actions if a["is_hold_action"]),
            "discarded_old_actions": self.queue.discarded_old_actions,
            "mean_action_delta_l2": statistics.mean(deltas) if deltas else float("nan"),
            "mean_action_acceleration_l2": mean_continuity([a["action_vector"] for a in self.actions], 2),
            "mean_action_jerk_l2": mean_continuity([a["action_vector"] for a in self.actions], 3),
        }
        return summary

    def _write_outputs(self) -> None:
        from .logging import ensure_dir, write_json, write_parquet

        requests_path = self.output_dir / "requests" / f"{self.episode_id}.parquet"
        actions_path = self.output_dir / "actions" / f"{self.episode_id}.parquet"
        episode_path = self.output_dir / "episodes" / f"{self.episode_id}.json"

        ensure_dir(requests_path.parent)
        ensure_dir(actions_path.parent)
        ensure_dir(episode_path.parent)

        if self.requests:
            write_parquet(requests_path, self.requests)
        if self.actions:
            write_parquet(actions_path, self.actions)
        summary = self._summarize(self._success, len(self.actions))
        write_json(episode_path, summary)


def run_episode(
    env: Any,
    policy: Any,
    preprocessor: Any,
    postprocessor: Any,
    task_instruction: str,
    *,
    episode_id: str,
    strategy: str,
    latency_profile: LatencyProfile,
    fixed_horizon: int,
    output_dir: Any,
    seed: int,
    use_rtc: bool = False,
    rtc_execution_horizon: int = 10,
    request_threshold_actions: Optional[int] = None,
    device: str = "cuda",
) -> dict[str, Any]:
    """High-level entry point to run one episode and write artifacts."""
    runner = EpisodeRunner(
        env=env,
        policy=policy,
        preprocessor=preprocessor,
        postprocessor=postprocessor,
        task_instruction=task_instruction,
        strategy=strategy,
        latency_profile=latency_profile,
        fixed_horizon=fixed_horizon,
        episode_id=episode_id,
        output_dir=output_dir,
        use_rtc=use_rtc,
        rtc_execution_horizon=rtc_execution_horizon,
        request_threshold_actions=request_threshold_actions,
        device=device,
    )
    return runner.run(seed)
