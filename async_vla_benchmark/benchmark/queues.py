"""Action queue primitives with explicit provenance."""

from collections import deque
from dataclasses import dataclass
import math
from typing import Any, Deque, Iterable, Optional


@dataclass(frozen=True)
class QueuedAction:
    value: Any
    chunk_id: str
    chunk_action_index: int
    source_observation_id: str
    source_observation_step: int
    raw_value: Any = None


class ActionQueue:
    def __init__(self, horizon: int):
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        self.horizon = horizon
        self._items: Deque[QueuedAction] = deque()
        self.outstanding_request_id: Optional[str] = None
        self.discarded_old_actions = 0

    @property
    def request_threshold(self) -> int:
        return math.ceil(self.horizon / 2)

    def __len__(self) -> int:
        return len(self._items)

    def should_request(self) -> bool:
        return len(self) <= self.request_threshold and self.outstanding_request_id is None

    def begin_request(self, request_id: str) -> None:
        if self.outstanding_request_id is not None:
            raise RuntimeError("only one policy request may be outstanding")
        self.outstanding_request_id = request_id

    def pop(self) -> Optional[QueuedAction]:
        return self._items.popleft() if self._items else None

    def remainder(self) -> tuple[QueuedAction, ...]:
        return tuple(self._items)

    def replace(self, request_id: str, actions: Iterable[QueuedAction]) -> None:
        if request_id != self.outstanding_request_id:
            raise RuntimeError("response does not match the outstanding request")
        incoming = list(actions)
        self.discarded_old_actions += len(self._items)
        self._items.clear()
        self._items.extend(incoming[: self.horizon])
        self.outstanding_request_id = None

    def startup(self, actions: Iterable[QueuedAction]) -> None:
        if self._items or self.outstanding_request_id is not None:
            raise RuntimeError("startup is only valid for an empty idle queue")
        incoming = list(actions)
        if len(incoming) < self.horizon:
            raise ValueError("startup chunk is shorter than configured horizon")
        self._items.extend(incoming[: self.horizon])
