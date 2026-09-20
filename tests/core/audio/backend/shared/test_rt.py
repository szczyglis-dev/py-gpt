from pygpt_net.core.audio.backend.shared.rt import build_output_volume_event, build_rt_input_delta_event
from pygpt_net.core.events import RealtimeEvent


def test_build_rt_input_delta_event_normalizes_payload():
    event = build_rt_input_delta_event("16000", "1", b"abc", 1)
    assert event.name == RealtimeEvent.RT_INPUT_AUDIO_DELTA
    assert event.data == {
        "payload": {
            "data": b"abc",
            "mime": "audio/pcm",
            "rate": 16000,
            "channels": 1,
            "final": True,
        }
    }


def test_build_rt_input_delta_event_uses_empty_bytes_for_none():
    event = build_rt_input_delta_event(8000, 2, None, False)
    assert event.data["payload"]["data"] == b""


def test_build_output_volume_event_casts_value():
    event = build_output_volume_event("42")
    assert event.name == RealtimeEvent.RT_OUTPUT_AUDIO_VOLUME_CHANGED
    assert event.data == {"volume": 42}
