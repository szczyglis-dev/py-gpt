from unittest.mock import MagicMock

from pygpt_net.core.events import Event
from pygpt_net.core.types import MODE_AGENT
from pygpt_net.plugin.experts import Plugin
from tests.mocks import mock_window


def test_experts_plugin_registers_inline_expert_command(mock_window):
    plugin = Plugin(window=mock_window)
    assert "expert" in plugin.type
    assert "cmd.inline" in plugin.type
    assert plugin.cmd_allowed("expert_call") is True


def test_experts_cmd_syntax_advertises_expert_call_once(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.experts.get_functions.return_value = [
        {"cmd": "expert_call", "instruction": "delegate", "params": []}
    ]
    data = {"cmd": []}

    plugin.cmd_syntax(data)
    plugin.cmd_syntax(data)

    assert data["cmd"] == [
        {"cmd": "expert_call", "instruction": "delegate", "params": []}
    ]


def test_experts_system_prompt_appends_expert_prompt(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.config.set("mode", "chat")
    mock_window.core.experts.get_prompt.return_value = "EXPERTS"
    assert plugin.on_system_prompt("base") == "base\n\nEXPERTS"
    assert plugin.on_system_prompt("") == "EXPERTS"


def test_experts_handle_skips_nested_expert_and_disallowed_mode(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.experts.get_prompt.return_value = "EXPERTS"
    event = Event()
    event.name = Event.SYSTEM_PROMPT
    event.data = {"value": "base", "is_expert": True}
    event.ctx = None
    mock_window.core.config.set("mode", "chat")
    plugin.handle(event)
    assert event.data["value"] == "base"

    event.data = {"value": "base"}
    mock_window.core.config.set("mode", MODE_AGENT)
    plugin.handle(event)
    assert event.data["value"] == "base"

    mock_window.core.config.set("mode", "chat")
    plugin.handle(event)
    assert event.data["value"] == "base\n\nEXPERTS"
