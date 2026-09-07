from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QEvent

from pygpt_net.ui.widget.tabs.layout import OutputColumn, OutputLayout, FocusEventFilter


def test_output_column_focus_updates_controller_and_focuses_widget():
    child = MagicMock()
    child.hasFocus.return_value = False
    widget = SimpleNamespace(idx=2, window=MagicMock())

    OutputColumn.on_focus(widget, child)

    widget.window.controller.ui.tabs.on_column_focus.assert_called_once_with(2)
    child.setFocus.assert_called_once()


def test_output_column_focus_does_not_refocus_already_focused_widget():
    child = MagicMock()
    child.hasFocus.return_value = True
    widget = SimpleNamespace(idx=1, window=MagicMock())

    OutputColumn.on_focus(widget, child)

    child.setFocus.assert_not_called()


def test_output_column_accessors():
    widget = SimpleNamespace(idx=-1, tabs="old")
    OutputColumn.set_idx(widget, 4)
    assert OutputColumn.get_idx(widget) == 4
    OutputColumn.set_tabs(widget, "new")
    assert OutputColumn.get_tabs(widget) == "new"


def test_output_layout_splitter_notifies_only_when_visibility_state_changes():
    splitter = MagicMock()
    splitter.count.return_value = 2
    widget = SimpleNamespace(splitter=splitter, _was_width_zero=None, window=MagicMock())

    splitter.sizes.return_value = [500, 0]
    OutputLayout.handle_splitter_moved(widget, 0, 1)
    OutputLayout.handle_splitter_moved(widget, 0, 1)
    widget.window.controller.ui.tabs.on_split_screen_changed.assert_called_once_with(False)

    splitter.sizes.return_value = [300, 200]
    OutputLayout.handle_splitter_moved(widget, 0, 1)
    widget.window.controller.ui.tabs.on_split_screen_changed.assert_called_with(True)
    assert widget.window.controller.ui.tabs.on_split_screen_changed.call_count == 2


def test_output_layout_column_management_and_lookup():
    first = SimpleNamespace(idx=9, tabs="first", set_idx=MagicMock())
    second = SimpleNamespace(idx=7, tabs="second", set_idx=MagicMock())
    widget = SimpleNamespace(columns=[])
    widget.get_next_idx = lambda: OutputLayout.get_next_idx(widget)

    OutputLayout.add_column(widget, first)
    first.idx = 0
    OutputLayout.add_column(widget, second)
    second.idx = 1

    assert OutputLayout.get_next_idx(widget) == 2
    assert OutputLayout.get_column_by_idx(widget, 0) is first
    assert OutputLayout.get_column_by_idx(widget, 1) is second
    assert OutputLayout.get_column_by_idx(widget, 99) is None
    widget.get_column_by_idx = lambda idx: OutputLayout.get_column_by_idx(widget, idx)
    assert OutputLayout.get_tabs_by_idx(widget, 1) == "second"


def test_output_layout_lookup_falls_back_to_column_idx_when_list_position_differs():
    target = SimpleNamespace(idx=5, tabs="target")
    widget = SimpleNamespace(columns=[SimpleNamespace(idx=1), target])
    assert OutputLayout.get_column_by_idx(widget, 5) is target


def test_output_layout_active_helpers_use_controller_current_column():
    column = SimpleNamespace(idx=3, tabs="tabs")
    window = MagicMock()
    window.controller.ui.tabs.get_current_column_idx.return_value = 3
    widget = SimpleNamespace(window=window, columns=[column])
    widget.get_column_by_idx = lambda idx: OutputLayout.get_column_by_idx(widget, idx)

    assert OutputLayout.get_active_tabs(widget) == "tabs"
    assert OutputLayout.get_active_column(widget) is column


def test_focus_event_filter_calls_callback_for_mouse_press_and_focus_in():
    column = object()
    callback = MagicMock()
    widget = SimpleNamespace(_column_ref=lambda: column, _callback=callback)
    obj = object()

    for event_type in (QEvent.MouseButtonPress, QEvent.FocusIn):
        event = MagicMock()
        event.type.return_value = event_type
        assert FocusEventFilter.eventFilter(widget, obj, event) is False

    assert callback.call_count == 2
    callback.assert_called_with(obj)


def test_focus_event_filter_ignores_other_events_and_dead_column():
    callback = MagicMock()
    event = MagicMock()
    event.type.return_value = QEvent.KeyPress
    widget = SimpleNamespace(_column_ref=lambda: object(), _callback=callback)
    FocusEventFilter.eventFilter(widget, object(), event)
    callback.assert_not_called()

    event.type.return_value = QEvent.FocusIn
    widget._column_ref = lambda: None
    FocusEventFilter.eventFilter(widget, object(), event)
    callback.assert_not_called()
