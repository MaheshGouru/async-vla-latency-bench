"""Dependency-free discrete-event execution state and provenance."""

from dataclasses import dataclass
from typing import Any, Optional


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
    return age_steps * control_period_seconds * 1000.0


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
