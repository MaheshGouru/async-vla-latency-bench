"""Episode-level continuity and distribution metrics."""

import math
from statistics import mean
from typing import Iterable, Sequence


def percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        return math.nan
    if not 0 <= probability <= 1:
        raise ValueError("probability must be in [0, 1]")
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    weight = index - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def l2_differences(actions: Iterable[Sequence[float]], order: int = 1) -> list[float]:
    rows = [list(map(float, row[:6])) for row in actions]
    for _ in range(order):
        rows = [[b - a for a, b in zip(left, right)] for left, right in zip(rows, rows[1:])]
    return [math.sqrt(sum(value * value for value in row)) for row in rows]


def mean_continuity(actions: Iterable[Sequence[float]], order: int) -> float:
    values = l2_differences(actions, order)
    return mean(values) if values else math.nan
