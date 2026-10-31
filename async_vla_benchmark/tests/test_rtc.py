import pytest

from async_vla_benchmark.benchmark.latency import (
    LatencyProfile,
    estimate_inference_delay_steps,
)
from async_vla_benchmark.benchmark.rtc import (
    configure_rtc,
    predict_rtc_chunk,
    rtc_action_counts,
)
from async_vla_benchmark.scripts.validate_results import (
    _check_rtc_action_counts,
    _check_rtc_inference_delay,
)


class FakePolicy:
    def predict_action_chunk(self, observation, **kwargs):
        return observation, kwargs


class FakeRTCConfig:
    def __init__(self, enabled=True):
        self.enabled = enabled


class FakePolicyConfig:
    """Mirrors PI05Config: rtc_config defaults to None, which disables RTC."""

    def __init__(self):
        self.rtc_config = None


class FakeRTCPolicy(FakePolicy):
    """Mirrors PI05Policy's RTC setup: init_rtc_processor() builds the processor
    from config.rtc_config, and leaves it None when that config is absent."""

    def __init__(self):
        self.config = FakePolicyConfig()
        self.rtc_processor = None

    def init_rtc_processor(self):
        self.rtc_processor = (
            object() if self.config.rtc_config is not None else None
        )

    def rtc_enabled(self):
        return self.config.rtc_config is not None and self.config.rtc_config.enabled


class TensorOnlyRTCPolicy(FakePolicy):
    """Mirrors the one thing LeRobot does to the remainder that numpy cannot.

    `RTCProcessor.denoise_step` calls `prev_chunk_left_over.unsqueeze(0)`, so a
    numpy array raises AttributeError mid-denoise. A fake that merely records its
    kwargs cannot catch that -- which is exactly why the numpy remainder shipped.
    """

    def predict_action_chunk(self, observation, **kwargs):
        kwargs["prev_chunk_left_over"].unsqueeze(0)
        return observation, kwargs


def test_rtc_receives_request_specific_inputs():
    torch = pytest.importorskip("torch")
    numpy = pytest.importorskip("numpy")

    remainder = numpy.zeros((3, 7), dtype=numpy.float64)
    _, kwargs = predict_rtc_chunk(
        FakePolicy(), {}, delay_steps=7, previous_chunk_remainder=remainder, execution_horizon=5
    )
    assert kwargs["inference_delay"] == 7
    assert kwargs["execution_horizon"] == 5
    # The remainder must arrive as a float32 tensor, not the numpy array built by
    # execution.py's np.stack.
    passed = kwargs["prev_chunk_left_over"]
    assert isinstance(passed, torch.Tensor)
    assert passed.dtype == torch.float32
    assert passed.shape == (3, 7)


def test_previous_chunk_remainder_survives_lerobot_tensor_api():
    """Regression: a numpy remainder crashed the first RTC episode of every run."""
    pytest.importorskip("torch")
    numpy = pytest.importorskip("numpy")

    _, kwargs = predict_rtc_chunk(
        TensorOnlyRTCPolicy(),
        {},
        delay_steps=4,
        previous_chunk_remainder=numpy.zeros((2, 7)),
        execution_horizon=5,
    )
    assert kwargs["prev_chunk_left_over"].shape == (2, 7)


def test_absent_remainder_is_passed_through_untouched():
    """The first request of an episode has no previous chunk to stay consistent with."""
    _, kwargs = predict_rtc_chunk(
        FakePolicy(), {}, delay_steps=0, previous_chunk_remainder=None, execution_horizon=5
    )
    assert kwargs["prev_chunk_left_over"] is None


def test_configure_rtc_activates_the_processor():
    """Regression: configure_rtc() existed but was never called, so rtc_config
    stayed None (its PI05Config default, and what the checkpoint ships).
    LeRobot then reported rtc_enabled=False and forwarded the per-request RTC
    arguments without ever applying guidance -- the 'rtc' arm silently ran
    without RTC. Passing the request kwargs is not sufficient on its own.
    """
    policy = FakeRTCPolicy()
    assert not policy.rtc_enabled(), "unconfigured policy must report RTC disabled"

    configure_rtc(policy, FakeRTCConfig())

    assert policy.rtc_enabled()
    assert policy.rtc_processor is not None


def test_configure_rtc_rejects_a_disabled_config():
    """A disabled config must fail loudly rather than silently running without
    guidance, which is the failure mode this whole check exists to prevent."""
    policy = FakeRTCPolicy()
    with pytest.raises(RuntimeError, match="active RTC processor"):
        configure_rtc(policy, FakeRTCConfig(enabled=False))


NATIVE = LatencyProfile("native", use_measured_native_latency=True, added_latency_ms=0.0)
CONTROL_PERIOD = 0.05  # 20 Hz, the resolved LIBERO control frequency


def test_inference_delay_uses_the_latest_measurement_not_an_average():
    """Regression: the estimate was the mean of every prior request in the episode,
    which is the global average spec section 15 forbids. Averaging 400 and 460 ms
    yields 430 ms -> 9 steps; the latest measurement alone yields 460 ms -> 10.
    """
    assert estimate_inference_delay_steps([400.0, 460.0], NATIVE, CONTROL_PERIOD) == 10


def test_inference_delay_is_zero_before_any_measurement_exists():
    """The startup request has no prior measurement, and runs under the ideal
    profile, so a zero here is correct rather than the hardcoded-zero defect."""
    assert estimate_inference_delay_steps([], NATIVE, CONTROL_PERIOD) == 0


@pytest.mark.parametrize(
    "inference_delay,overlap,horizon,effective,frozen,guided",
    [
        (3, 5, 10, 5, 3, 2),  # horizon clamped down to the remainder
        (3, 5, 2, 2, 2, 0),   # remainder longer than the horizon
        (8, 5, 10, 5, 5, 0),  # response outlives the overlap: nothing left to guide
        (0, 10, 10, 10, 0, 10),
        (3, 0, 10, 0, 0, 0),  # empty queue at request time: no prefix at all
    ],
)
def test_rtc_action_counts(inference_delay, overlap, horizon, effective, frozen, guided):
    assert rtc_action_counts(
        inference_delay_steps=inference_delay,
        overlap_actions=overlap,
        execution_horizon=horizon,
    ) == {
        "overlap_actions": overlap,
        "effective_execution_horizon": effective,
        "frozen_prefix_actions": frozen,
        "guided_actions": guided,
    }


def _request(request_id, *, delay_steps, inference_delay):
    return {
        "request_id": request_id,
        "delay_steps": delay_steps,
        "rtc_inference_delay_steps": inference_delay,
    }


RTC_SUMMARY = {"strategy": "rtc"}


def test_validator_rejects_a_constant_inference_delay():
    """The global-average signature: what RTC receives never moves while the delays
    the requests actually incur do."""
    requests = [
        _request("r0", delay_steps=8, inference_delay=9),
        _request("r1", delay_steps=10, inference_delay=9),
        _request("r2", delay_steps=9, inference_delay=9),
    ]
    errors = _check_rtc_inference_delay(RTC_SUMMARY, requests)
    assert any("constant inference_delay" in e for e in errors)


def test_validator_rejects_the_hardcoded_zero_delay():
    """The exact pre-fix defect. The old check read delay_steps, which stayed
    request-specific throughout, so it reported these episodes as clean."""
    requests = [
        _request("r0", delay_steps=8, inference_delay=0),
        _request("r1", delay_steps=10, inference_delay=0),
    ]
    errors = _check_rtc_inference_delay(RTC_SUMMARY, requests)
    assert any("inference_delay=0" in e for e in errors)


def test_validator_accepts_request_specific_delays():
    requests = [
        _request("r0", delay_steps=8, inference_delay=8),
        _request("r1", delay_steps=10, inference_delay=9),
        _request("r2", delay_steps=9, inference_delay=10),
    ]
    assert _check_rtc_inference_delay(RTC_SUMMARY, requests) == []


def test_validator_skips_records_predating_the_field():
    """Days 1-3 episodes carry no rtc_inference_delay_steps; they must stay
    validatable rather than fail on an absent column."""
    requests = [{"request_id": "r0", "delay_steps": 8}]
    assert _check_rtc_inference_delay(RTC_SUMMARY, requests) == []


def test_validator_rejects_inconsistent_action_counts():
    requests = [
        {
            "request_id": "r0",
            "rtc_overlap_actions": 5,
            "rtc_effective_execution_horizon": 5,
            "rtc_frozen_prefix_actions": 3,
            "rtc_guided_actions": 4,  # 3 + 4 != 5
        }
    ]
    errors = _check_rtc_action_counts(RTC_SUMMARY, requests)
    assert any("!= effective execution horizon" in e for e in errors)


def test_validator_rejects_an_unclamped_execution_horizon():
    """LeRobot clamps the horizon to the remainder length; a record claiming
    otherwise means the counts describe a run that cannot have happened."""
    requests = [
        {
            "request_id": "r0",
            "rtc_overlap_actions": 4,
            "rtc_effective_execution_horizon": 10,
            "rtc_frozen_prefix_actions": 0,
            "rtc_guided_actions": 10,
        }
    ]
    errors = _check_rtc_action_counts(RTC_SUMMARY, requests)
    assert any("exceeds" in e for e in errors)


def test_validator_ignores_non_rtc_strategies():
    requests = [_request("r0", delay_steps=8, inference_delay=0)]
    assert _check_rtc_inference_delay({"strategy": "naive_async"}, requests) == []
    assert _check_rtc_action_counts({"strategy": "naive_async"}, requests) == []
