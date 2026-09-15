from unittest.mock import MagicMock

import pygpt_net.core.access.access as access_module
from pygpt_net.core.access.access import Access


def test_access_builds_all_subcomponents_with_same_window(monkeypatch):
    window = object()
    actions = MagicMock(return_value="actions")
    helpers = MagicMock(return_value="helpers")
    shortcuts = MagicMock(return_value="shortcuts")
    voice = MagicMock(return_value="voice")
    monkeypatch.setattr(access_module, "Actions", actions)
    monkeypatch.setattr(access_module, "Helpers", helpers)
    monkeypatch.setattr(access_module, "Shortcuts", shortcuts)
    monkeypatch.setattr(access_module, "Voice", voice)

    core = Access(window)

    assert core.window is window
    assert (core.actions, core.helpers, core.shortcuts, core.voice) == ("actions", "helpers", "shortcuts", "voice")
    actions.assert_called_once_with(window)
    helpers.assert_called_once_with(window)
    shortcuts.assert_called_once_with(window)
    voice.assert_called_once_with(window)
