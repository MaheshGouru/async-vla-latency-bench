from async_vla_benchmark.benchmark.rtc import predict_rtc_chunk


class FakePolicy:
    def predict_action_chunk(self, observation, **kwargs):
        return observation, kwargs


def test_rtc_receives_request_specific_inputs():
    remainder = object()
    _, kwargs = predict_rtc_chunk(
        FakePolicy(), {}, delay_steps=7, previous_chunk_remainder=remainder, execution_horizon=5
    )
    assert kwargs == {
        "inference_delay": 7,
        "prev_chunk_left_over": remainder,
        "execution_horizon": 5,
    }
