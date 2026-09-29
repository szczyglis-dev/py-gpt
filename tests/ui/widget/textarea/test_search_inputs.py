from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.textarea.search_input import CtxSearchInput, SearchInput
from pygpt_net.ui.widget.textarea.find import FindInput


def test_context_search_text_change_toggles_clear_and_restarts_timer():
    widget = SimpleNamespace(clear_action=MagicMock(), _search_timer=MagicMock())

    CtxSearchInput.on_text_changed(widget, "abc")
    widget.clear_action.setVisible.assert_called_once_with(True)
    widget._search_timer.start.assert_called_once()


def test_context_search_clear_stops_timer_and_controller_search():
    widget = SimpleNamespace(clear=MagicMock(), _search_timer=MagicMock(), window=MagicMock())

    CtxSearchInput.clear_search_string(widget)

    widget.clear.assert_called_once()
    widget._search_timer.stop.assert_called_once()
    widget.window.controller.ctx.search_string_clear.assert_called_once()


def test_context_search_execute_uses_current_text():
    widget = SimpleNamespace(text=lambda: "needle", window=MagicMock())
    CtxSearchInput._execute_search(widget)
    widget.window.controller.ctx.search_string_change.assert_called_once_with("needle")


def test_generic_search_callbacks_are_optional_and_receive_text():
    on_search = MagicMock()
    on_clear = MagicMock()
    widget = SimpleNamespace(
        clear=MagicMock(),
        _search_timer=MagicMock(),
        clear_action=MagicMock(),
        text=lambda: "needle",
        on_search=on_search,
        on_clear=on_clear,
    )

    SearchInput.on_text_changed(widget, "needle")
    SearchInput._execute_search(widget)
    SearchInput.clear_search_string(widget)

    widget.clear_action.setVisible.assert_called_once_with(True)
    on_search.assert_called_once_with("needle")
    on_clear.assert_called_once()


def test_find_input_text_change_forwards_to_finder():
    widget = SimpleNamespace(window=MagicMock())
    FindInput._on_text_changed(widget, "query")
    widget.window.controller.finder.search_text_changed.assert_called_once_with("query")


def test_find_input_enter_and_focus_forward_current_text(qapp):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QFocusEvent, QKeyEvent

    window = MagicMock()
    widget = FindInput(None, "find")
    widget.window = window
    widget.setText("needle")

    widget.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
    widget.focusInEvent(QFocusEvent(QEvent.FocusIn))

    assert window.controller.finder.focus_input.call_count == 2
    window.controller.finder.focus_input.assert_called_with("needle")


def test_find_input_non_enter_does_not_force_focus_search(qapp):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    window = MagicMock()
    widget = FindInput(None, "find")
    widget.window = window
    widget.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    window.controller.finder.focus_input.assert_not_called()
