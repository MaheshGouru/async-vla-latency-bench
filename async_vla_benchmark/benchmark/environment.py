"""Lazy LIBERO environment integration and control-frequency resolution."""

from typing import Any


class EnvironmentUnavailable(RuntimeError):
    pass


def require_lerobot_libero() -> None:
    try:
        import lerobot  # noqa: F401
        import libero  # noqa: F401
    except ImportError as exc:
        raise EnvironmentUnavailable(
            "LeRobot/LIBERO is not installed. Install a pinned LeRobot checkout with "
            "the pi and libero extras in the Linux CUDA execution environment."
        ) from exc


def resolve_control_frequency_hz(environment: Any) -> float:
    """Resolve an explicitly exposed frequency; never invent a default."""
    candidates = [
        getattr(environment, "control_freq", None),
        getattr(environment, "control_frequency", None),
        getattr(environment, "metadata", {}).get("control_frequency_hz")
        if isinstance(getattr(environment, "metadata", None), dict)
        else None,
    ]
    unwrapped = getattr(environment, "unwrapped", None)
    if unwrapped is not None:
        candidates.extend(
            [getattr(unwrapped, "control_freq", None), getattr(unwrapped, "control_frequency", None)]
        )
    for value in candidates:
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    raise EnvironmentUnavailable(
        "LIBERO environment did not expose a reliable control frequency; inspect the pinned "
        "environment revision and add an explicit adapter before running episodes."
    )
