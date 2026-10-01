from unittest.mock import MagicMock

import pytest

from pygpt_net.plugin.audio_input.simple import Simple


@pytest.mark.parametrize("started", [True, False])
def test_start_opens_capture_without_probe_and_handles_failure(started, monkeypatch):
    monkeypatch.setattr("pygpt_net.plugin.audio_input.simple.trans", lambda key: key)
    plugin = MagicMock()
    window = plugin.window
    window.core.config.get.side_effect = lambda key, default=None: {
        "audio.input.snap": True,
        "audio.input.timeout": 0,
    }.get(key, default)
    window.core.config.has.return_value = True
    window.core.platforms.is_snap.return_value = False
    capture = window.core.audio.capture
    capture.start.return_value = started
    handler = Simple(plugin)
    timer = MagicMock()
    handler.timer = timer

    handler.start_recording()

    capture.check_audio_input.assert_not_called()
    capture.start.assert_called_once()
    assert handler.is_recording is started
    if started:
        window.controller.audio.ui.on_input_begin.assert_called_once_with("input")
    else:
        window.controller.audio.ui.on_input_begin.assert_not_called()
        window.controller.audio.ui.on_input_abort.assert_called_once_with("input")
        timer.stop.assert_called_once()
        assert handler.timer is None
        window.dispatch.assert_not_called()


@pytest.mark.parametrize("vad", [False, True])
@pytest.mark.parametrize("explicit_state", [False, None])
def test_ordinary_stop_submits_even_short_recording_with_saved_vad(vad, explicit_state):
    plugin = MagicMock()
    plugin.window.controller.realtime.is_enabled.return_value = False
    plugin.window.controller.realtime.is_auto_turn.return_value = vad
    capture = plugin.window.core.audio.capture
    capture.has_source.return_value = True
    capture.has_frames.return_value = True
    capture.has_min_frames.return_value = True
    handler = Simple(plugin)
    handler.is_recording = True

    handler.toggle_recording(state=explicit_state)

    capture.stop.assert_called_once()
    capture.start.assert_not_called()
    plugin.handle_thread.assert_called_once_with(True)
    assert handler.is_recording is False


@pytest.mark.parametrize("enabled,vad,submit", [(False, True, True), (True, False, True), (True, True, False)])
def test_stop_only_skips_file_submission_for_active_realtime_vad(enabled, vad, submit):
    plugin = MagicMock()
    plugin.window.controller.realtime.is_enabled.return_value = enabled
    plugin.window.controller.realtime.is_auto_turn.return_value = vad
    handler = Simple(plugin)
    handler.is_recording = True

    handler.stop_recording(realtime=True)

    assert plugin.handle_thread.call_count == int(submit)
    plugin.window.core.audio.capture.start.assert_not_called()


@pytest.mark.parametrize("has_frames", [False, True])
@pytest.mark.parametrize("action", ["mic", "stop", "send"])
def test_short_recording_reports_global_status_without_transcribing(monkeypatch, has_frames, action):
    from pygpt_net.controller.chat.common import Common

    monkeypatch.setattr("pygpt_net.plugin.audio_input.simple.trans", lambda key: "Recording too short")
    plugin = MagicMock()
    window = plugin.window
    window.controller.realtime.is_enabled.return_value = False
    capture = window.core.audio.capture
    capture.has_source.return_value = True
    capture.has_frames.return_value = has_frames
    capture.has_min_frames.return_value = False
    handler = Simple(plugin)
    handler.is_recording = True
    window.core.plugins.get.return_value.handler_simple = handler
    common = Common(window)

    if action == "mic":
        handler.toggle_recording()
    elif action == "stop":
        common.handle_stop()
    else:
        common.handle_send()

    window.update_status.assert_called_with("Recording too short")
    plugin.handle_thread.assert_not_called()
    assert handler.is_recording is False
