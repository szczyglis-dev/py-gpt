from pygpt_net.core.events import Event
from pygpt_net.plugin.extra_prompt import Plugin
from tests.mocks import mock_window


def test_extra_prompt_defaults_empty(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin.get_option_value("prompts") == []
    assert plugin.on_system_prompt("base") == "base\n"


def test_extra_prompt_appends_only_enabled_items(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("prompts", [
        {"enabled": True, "name": "a", "prompt": "A"},
        {"enabled": False, "name": "b", "prompt": "B"},
        {"enabled": True, "name": "c", "prompt": "C"},
    ])
    assert plugin.on_system_prompt("base") == "base\nA\nC"


def test_extra_prompt_handle_updates_system_prompt(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("prompts", [{"enabled": True, "name": "a", "prompt": "A"}])
    event = Event()
    event.name = Event.SYSTEM_PROMPT
    event.data = {"value": "base"}
    event.ctx = None
    plugin.handle(event)
    assert event.data["value"] == "base\nA"
