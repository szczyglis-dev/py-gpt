from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6 import QtCore

from pygpt_net.ui.widget.textarea.console import ConsoleInput


def _console(**overrides):
    data = dict(
        _commands=[],
        _history=[],
        _history_index=0,
        _in_history_mode=False,
        _buffer_before_history="",
        text=lambda: "",
        setText=MagicMock(),
        end=MagicMock(),
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_console_history_deduplicates_consecutive_commands_and_resets_index():
    widget = _console(_history=["one"], _history_index=0, _in_history_mode=True, _buffer_before_history="x")

    ConsoleInput.add_to_history(widget, "one")
    ConsoleInput.add_to_history(widget, " two ")
    ConsoleInput.add_to_history(widget, "")

    assert widget._history == ["one", " two "]
    assert widget._history_index == 2
    assert widget._in_history_mode is False
    assert widget._buffer_before_history == ""


def test_console_history_previous_preserves_current_buffer():
    widget = _console(_history=["one", "two"], _history_index=2, text=lambda: "draft")

    ConsoleInput._history_prev(widget)

    assert widget._buffer_before_history == "draft"
    assert widget._in_history_mode is True
    assert widget._history_index == 1
    widget.setText.assert_called_once_with("two")
    widget.end.assert_called_once_with(False)


def test_console_history_next_restores_buffer_after_last_item():
    widget = _console(
        _history=["one", "two"],
        _history_index=1,
        _in_history_mode=True,
        _buffer_before_history="draft",
    )

    ConsoleInput._history_next(widget)

    assert widget._history_index == 2
    assert widget._in_history_mode is False
    assert widget._buffer_before_history == ""
    widget.setText.assert_called_once_with("draft")


def test_longest_common_prefix():
    widget = SimpleNamespace()
    assert ConsoleInput._longest_common_prefix(widget, []) == ""
    assert ConsoleInput._longest_common_prefix(widget, ["help", "hello", "helm"]) == "hel"
    assert ConsoleInput._longest_common_prefix(widget, ["same"]) == "same"


def test_autocomplete_single_match_is_case_insensitive():
    widget = _console(_commands=["Help", "clear"], text=lambda: "he")

    assert ConsoleInput._try_autocomplete(widget) is True
    widget.setText.assert_called_once_with("Help")
    widget.end.assert_called_once_with(False)


def test_autocomplete_multiple_matches_extends_common_prefix():
    widget = _console(_commands=["history", "histogram"], text=lambda: "his")
    widget._longest_common_prefix = lambda values: ConsoleInput._longest_common_prefix(widget, values)

    assert ConsoleInput._try_autocomplete(widget) is True
    widget.setText.assert_called_once_with("histo")


def test_autocomplete_rejects_arguments_or_no_commands():
    assert ConsoleInput._try_autocomplete(_console(_commands=[], text=lambda: "he")) is False
    assert ConsoleInput._try_autocomplete(_console(_commands=["help"], text=lambda: "help now")) is False


def test_console_enter_dispatches_send_and_accepts_event():
    event = MagicMock()
    event.key.return_value = QtCore.Qt.Key_Return
    widget = _console(window=MagicMock(), setFocus=MagicMock())

    ConsoleInput.keyPressEvent(widget, event)

    widget.window.core.debug.console.on_send.assert_called_once()
    widget.setFocus.assert_called_once()
    event.accept.assert_called_once()


def test_focus_traversal_is_disabled():
    assert ConsoleInput.focusNextPrevChild(SimpleNamespace(), True) is False


def test_set_commands_accepts_list_or_tuple_and_ignores_other_types():
    widget = _console(_commands=["old"])

    ConsoleInput.set_commands(widget, ("help", "clear"))
    assert widget._commands == ["help", "clear"]

    ConsoleInput.set_commands(widget, "history")
    assert widget._commands == ["help", "clear"]


def test_history_navigation_beeps_on_empty_or_invalid_direction():
    widget = _console(_history=[])
    with patch("pygpt_net.ui.widget.textarea.console.QApplication.beep") as beep:
        ConsoleInput._history_prev(widget)
        ConsoleInput._history_next(widget)
    assert beep.call_count == 2

    widget = _console(_history=["one"], _history_index=1, _in_history_mode=False)
    with patch("pygpt_net.ui.widget.textarea.console.QApplication.beep") as beep:
        ConsoleInput._history_next(widget)
    beep.assert_called_once()


def test_history_previous_at_oldest_item_beeps_without_changing_text():
    widget = _console(_history=["one"], _history_index=0, _in_history_mode=True)
    with patch("pygpt_net.ui.widget.textarea.console.QApplication.beep") as beep:
        ConsoleInput._history_prev(widget)
    beep.assert_called_once()
    widget.setText.assert_not_called()


def test_console_up_down_and_tab_keys_delegate_and_accept_event():
    widget = _console(_history_prev=MagicMock(), _history_next=MagicMock(), _try_autocomplete=MagicMock(return_value=True))

    for key, expected in (
        (QtCore.Qt.Key_Up, widget._history_prev),
        (QtCore.Qt.Key_Down, widget._history_next),
        (QtCore.Qt.Key_Tab, widget._try_autocomplete),
    ):
        event = MagicMock()
        event.key.return_value = key
        ConsoleInput.keyPressEvent(widget, event)
        expected.assert_called_once()
        expected.reset_mock()
        event.accept.assert_called_once()


def test_console_failed_tab_autocomplete_beeps_and_accepts_event():
    widget = _console(_try_autocomplete=MagicMock(return_value=False))
    event = MagicMock()
    event.key.return_value = QtCore.Qt.Key_Backtab

    with patch("pygpt_net.ui.widget.textarea.console.QApplication.beep") as beep:
        ConsoleInput.keyPressEvent(widget, event)

    beep.assert_called_once()
    event.accept.assert_called_once()
