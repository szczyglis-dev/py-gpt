from pygpt_net.core.audio.context import AudioContext


def test_audio_context_defaults_and_sorted_dictionary():
    assert AudioContext().to_dict() == {"data": None, "prev_id": None}
    ctx = AudioContext(ctx={"audio": 1}, prev_id="prev")
    result = ctx.to_dict()
    assert list(result) == ["data", "prev_id"]
    assert result == {"data": {"audio": 1}, "prev_id": "prev"}
