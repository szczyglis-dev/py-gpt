#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pygpt_net.core.realtime.options import RealtimeOptions


def test_realtime_options_defaults_are_independent_and_serializable():
    first = RealtimeOptions()
    second = RealtimeOptions()
    first.extra["x"] = 1

    assert second.extra == {}
    data = first.to_dict()
    assert data["provider"] == "openai"
    assert data["audio_data (len)"] == 0
    assert data["auto_turn"] is False
    assert data["transcribe"] is True
    assert data["extra"] == {"x": 1}
    assert "rt_signals" not in data


def test_realtime_options_to_dict_reports_audio_length_and_runtime_fields():
    options = RealtimeOptions(
        provider="google",
        model="m",
        system_prompt="system",
        prompt="hello",
        voice="voice",
        audio_data=b"1234",
        audio_format="pcm16",
        audio_rate=16000,
        vad="server_vad",
        tools=["tool"],
        remote_tools=["remote"],
        auto_turn=True,
        transcribe=False,
        rt_session_id="session",
        extra={"a": 1},
    )

    data = options.to_dict()

    assert data["provider"] == "google"
    assert data["audio_data (len)"] == 4
    assert data["audio_format"] == "pcm16"
    assert data["audio_rate"] == 16000
    assert data["vad"] == "server_vad"
    assert data["tools"] == ["tool"]
    assert data["remote_tools"] == ["remote"]
    assert data["rt_session_id"] == "session"
