from unittest.mock import MagicMock

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.voice_control import Plugin
from tests.mocks import mock_window


def test_voice_control_prepare_command_list(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.access.voice.get_inline_prompt.return_value = "  Voice instruction  "
    mock_window.core.access.voice.get_commands.return_value = ["mute", "volume"]
    cmd = plugin.prepare_cmd_list()
    assert cmd["cmd"] == "voice_cmd"
    assert cmd["instruction"] == "Voice instruction"
    assert cmd["params"][0]["enum"]["action"] == ["mute", "volume"]


def test_voice_control_syntax_for_inline_and_regular(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.prepare_cmd_list = MagicMock(return_value={"cmd": "voice_cmd"})
    for event_name in (Event.CMD_SYNTAX, Event.CMD_SYNTAX_INLINE):
        event = Event()
        event.name = event_name
        event.data = {"cmd": []}
        event.ctx = CtxItem()
        plugin.handle(event)
        assert event.data["cmd"] == [{"cmd": "voice_cmd"}]


def test_voice_control_enable_turns_on_audio_input(mock_window):
    plugin = Plugin(window=mock_window)
    event = Event()
    event.name = Event.ENABLE
    event.data = {"value": plugin.id}
    event.ctx = None
    plugin.handle(event)
    mock_window.controller.plugins.enable.assert_called_once_with("audio_input")


def test_voice_control_executes_known_and_unrecognized_actions(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.access.voice.get_commands.return_value = ["mute", "volume"]
    ctx = CtxItem()
    plugin.cmd(ctx, [
        {"cmd": "voice_cmd", "params": {"action": "mute", "args": "now"}},
        {"cmd": "voice_cmd", "params": {"action": "unknown"}},
        {"cmd": "other", "params": {}},
    ])
    mock_window.controller.access.voice.handle_commands.assert_called_once_with([
        {"cmd": "mute", "params": "now"},
        {"cmd": "unrecognized", "params": ""},
    ])


def test_voice_control_missing_action_aborts_without_execution(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.access.voice.get_commands.return_value = ["mute"]
    plugin.cmd(CtxItem(), [{"cmd": "voice_cmd", "params": {}}])
    mock_window.controller.access.voice.handle_commands.assert_not_called()


def test_voice_control_ignores_unrelated_commands(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd(CtxItem(), [{"cmd": "other", "params": {}}])
    mock_window.controller.access.voice.handle_commands.assert_not_called()
