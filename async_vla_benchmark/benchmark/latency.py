"""Request-specific latency measurement and logical-step conversion."""

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class LatencyProfile:
    name: str
    use_measured_native_latency: bool
    added_latency_ms: float = 0.0

    def logical_latency_ms(self, measured_request_latency_ms: float) -> float:
        if self.name == "ideal":
            return 0.0
        native = measured_request_latency_ms if self.use_measured_native_latency else 0.0
        total = native + self.added_latency_ms
        if total < 0:
            raise ValueError("logical latency cannot be negative")
        return total


def latency_to_delay_steps(latency_ms: float, control_period_seconds: float) -> int:
    """Convert arrival latency to missed control deadlines using ceil."""
    if latency_ms < 0:
        raise ValueError("latency_ms cannot be negative")
    if not math.isfinite(control_period_seconds) or control_period_seconds <= 0:
        raise ValueError("control_period_seconds must be finite and positive")
    return math.ceil(latency_ms / (control_period_seconds * 1000.0))


def request_delay_steps(
    profile: LatencyProfile,
    measured_request_latency_ms: float,
    control_period_seconds: float,
) -> int:
    return latency_to_delay_steps(
        profile.logical_latency_ms(measured_request_latency_ms), control_period_seconds
    )


def estimate_inference_delay_steps(
    prior_request_latencies_ms: Sequence[float],
    profile: LatencyProfile,
    control_period_seconds: float,
) -> int:
    """Predict this request's `delay_steps` for RTC's `inference_delay` argument.

    Spec section 15 requires the runtime `inference_delay` to reflect the current
    request's measured latency and explicitly forbids a global average. The current
    request's latency is not knowable until the call it parameterizes has already
    returned, so the closest admissible estimator is the single most recent measured
    request in this episode: one request-specific observation that tracks drift,
    rather than a mean over history (which is the global average the spec rules out).

    This remains an estimate. `execution.py` logs it next to the realized
    `delay_steps` on every request so the residual deviation is measured per request
    instead of assumed, and `validate_results.py` checks the logged value rather than
    the realized one.
    """
    if not prior_request_latencies_ms:
        return 0
    latest_measured_latency_ms = prior_request_latencies_ms[-1]
    return latency_to_delay_steps(
        profile.logical_latency_ms(latest_measured_latency_ms), control_period_seconds
    )
