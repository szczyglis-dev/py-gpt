from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.events import RenderEvent
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.plugin.audio_input.plugin import Plugin
from pygpt_net.plugin.audio_input.worker import Worker


def make_plugin():
    window = MagicMock()
    window.controller.realtime.is_enabled.return_value = False
    window.controller.tabs.get_current_type.return_value = Tab.TAB_CHAT
    window.core.ctx.output.has_request.return_value = False
    window.core.ctx.get_current_meta.return_value = SimpleNamespace(id=42)
    plugin = Plugin(window=window)
    plugin.is_advanced = MagicMock(return_value=False)
    plugin.get_input_path = MagicMock(return_value='/tmp/input.wav')
    return plugin, window


def test_loader_visible_before_transcription_is_scheduled():
    plugin, window = make_plugin()
    with patch('pygpt_net.plugin.audio_input.worker.Worker') as worker_cls:
        worker = worker_cls.return_value

        def run():
            event = window.dispatch.call_args.args[0]
            assert event.name == RenderEvent.STATE_BUSY
            assert event.data['loading_delay_ms'] == 0
            assert event.data['loading_wait_for_input'] is False
            assert worker.transcription_loader_token in plugin._transcription_loaders

        worker.run_async.side_effect = run
        plugin.handle_thread(True)
        worker.run_async.assert_called_once()
        worker.signals.capture_finished.connect.assert_called_once_with(plugin._finish_transcription_loader)


@pytest.mark.parametrize('realtime,tab', [(True, Tab.TAB_CHAT), (False, Tab.TAB_NOTEPAD)])
def test_loader_does_not_affect_realtime_or_notepad(realtime, tab):
    plugin, window = make_plugin()
    window.controller.realtime.is_enabled.return_value = realtime
    window.controller.tabs.get_current_type.return_value = tab
    assert plugin._begin_transcription_loader() is None
    window.dispatch.assert_not_called()


def test_transcription_cleanup_targets_original_chat_and_keeps_reply_loader():
    plugin, window = make_plugin()
    token = plugin._begin_transcription_loader()
    window.core.ctx.get_current_meta.return_value = SimpleNamespace(id=99)
    plugin._finish_transcription_loader(token)
    event = window.dispatch.call_args.args[0]
    assert event.name == RenderEvent.STATE_IDLE
    assert event.data['meta'].id == 42

    token = plugin._begin_transcription_loader()
    window.dispatch.reset_mock()
    window.core.ctx.output.has_request.return_value = True
    window.core.ctx.output.get_request_meta.return_value = SimpleNamespace(id=99)
    plugin._finish_transcription_loader(token)
    window.dispatch.assert_not_called()
    assert not plugin._transcription_loaders


def test_failed_worker_start_clears_loader():
    plugin, window = make_plugin()
    plugin.error = MagicMock()
    with patch('pygpt_net.plugin.audio_input.worker.Worker') as worker_cls:
        worker_cls.return_value.run_async.side_effect = RuntimeError('cannot start')
        plugin.handle_thread(True)
    assert window.dispatch.call_args.args[0].name == RenderEvent.STATE_IDLE
    assert not plugin._transcription_loaders


@pytest.mark.parametrize('fails', [False, True])
def test_worker_always_finishes_capture_loader_before_cleanup(monkeypatch, fails):
    worker = Worker()
    token = object()
    worker.transcription_loader_token = token
    worker.handle_simple = MagicMock(side_effect=RuntimeError('failed') if fails else None)
    worker.error = MagicMock()
    order = []
    monkeypatch.setattr('pygpt_net.plugin.audio_input.worker.safe_emit',
                        lambda signals, name, value: order.append((name, value)))
    worker.cleanup = lambda: order.append('cleanup')
    worker.run()
    assert order == [('capture_finished', token), 'cleanup']


def test_earlier_transcription_cannot_hide_newer_loader():
    plugin, window = make_plugin()
    first = plugin._begin_transcription_loader()
    second = plugin._begin_transcription_loader()
    window.dispatch.reset_mock()
    plugin._finish_transcription_loader(first)
    window.dispatch.assert_not_called()
    plugin._finish_transcription_loader(second)
    assert window.dispatch.call_args.args[0].name == RenderEvent.STATE_IDLE
