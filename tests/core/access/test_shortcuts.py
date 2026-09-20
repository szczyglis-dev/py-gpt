from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6 import QtCore
from PySide6.QtCore import QEvent

from pygpt_net.core.access.shortcuts import GlobalShortcutFilter, Shortcuts


def test_shortcut_choice_lists_include_letters_digits_functions_and_modifiers():
    shortcuts = Shortcuts()
    keys = shortcuts.get_keys_choices()
    assert {"A": "A"} in keys
    assert {"0": "0"} in keys
    assert {"F12": "F12"} in keys
    assert {"Escape": "Escape"} in keys
    assert shortcuts.get_modifiers_choices() == [
        {"---": "---"}, {"Ctrl": "Ctrl"}, {"Alt": "Alt"}, {"Shift": "Shift"},
    ]


def test_escape_is_handled_before_config_lookup():
    window = SimpleNamespace(controller=SimpleNamespace(access=SimpleNamespace(on_escape=MagicMock())))
    shortcuts = Shortcuts(window)
    event = MagicMock()
    event.type.return_value = QEvent.KeyPress
    event.key.return_value = QtCore.Qt.Key_Escape

    assert shortcuts.handle_global_shortcuts(event) is True
    window.controller.access.on_escape.assert_called_once_with()


def test_configured_shortcut_dispatches_control_event():
    config = [{"key": "A", "key_modifier": "Alt", "action": "ctx.new"}]
    window = SimpleNamespace(
        core=SimpleNamespace(config=SimpleNamespace(get=MagicMock(return_value=config))),
        dispatch=MagicMock(),
    )
    shortcuts = Shortcuts(window)
    event = MagicMock()
    event.type.return_value = QEvent.KeyPress
    event.key.return_value = QtCore.Qt.Key_A
    event.modifiers.return_value = QtCore.Qt.AltModifier

    assert shortcuts.handle_global_shortcuts(event) is True
    dispatched = window.dispatch.call_args.args[0]
    assert dispatched.name == "ctx.new"


def test_global_filter_delegates_only_key_press_events():
    handler = MagicMock(return_value=True)
    window = SimpleNamespace(
        controller=object(),
        core=SimpleNamespace(access=SimpleNamespace(shortcuts=SimpleNamespace(handle_global_shortcuts=handler))),
    )
    filt = GlobalShortcutFilter(window)
    event = MagicMock()
    event.type.return_value = QEvent.KeyPress

    assert filt.eventFilter(object(), event) is True
    handler.assert_called_once_with(event)

    event.type.return_value = QEvent.MouseMove
    assert filt.eventFilter(object(), event) is False
