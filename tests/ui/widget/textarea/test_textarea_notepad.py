from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.textarea.notepad import NotepadOutput, NotepadWidget


def test_notepad_widget_text_accessors_delegate_to_textarea():
    textarea = MagicMock()
    widget = SimpleNamespace(textarea=textarea)
    NotepadWidget.setText(widget, "hello")
    textarea.setText.assert_called_once_with("hello")
    textarea.on_update.assert_called_once_with()
    textarea.toPlainText.return_value = "world"
    assert NotepadWidget.toPlainText(widget) == "world"


def test_notepad_widget_set_tab_forwards_to_textarea():
    textarea = MagicMock()
    widget = SimpleNamespace(textarea=textarea)
    tab = object()
    NotepadWidget.set_tab(widget, tab)
    assert widget.tab is tab
    textarea.set_tab.assert_called_once_with(tab)


def test_sanitize_ranges_filters_invalid_and_sorts():
    widget = SimpleNamespace()
    ranges = [(5, 2), (-1, 4), (2, 0), ("3", "2"), ("x", 1), None]
    assert NotepadOutput._sanitize_ranges(widget, ranges) == [(3, 2), (5, 2)]
    assert NotepadOutput._sanitize_ranges(widget, None) == []


def test_merge_ranges_merges_overlapping_and_adjacent_ranges():
    widget = SimpleNamespace()
    assert NotepadOutput._merge_ranges(widget, []) == []
    assert NotepadOutput._merge_ranges(widget, [(0, 3), (3, 2), (10, 2), (11, 4)]) == [
        (0, 5),
        (10, 5),
    ]


def test_add_highlight_merges_and_schedules_save():
    widget = SimpleNamespace(
        _highlights=[(0, 3)],
        _sanitize_ranges=lambda ranges: NotepadOutput._sanitize_ranges(SimpleNamespace(), ranges),
        _merge_ranges=lambda ranges: NotepadOutput._merge_ranges(SimpleNamespace(), ranges),
        schedule_save=MagicMock(),
    )
    NotepadOutput._add_highlight(widget, (2, 5))
    assert widget._highlights == [(0, 7)]
    widget.schedule_save.assert_called_once_with()


def test_add_highlight_ignores_non_positive_length():
    widget = SimpleNamespace(_highlights=[], schedule_save=MagicMock())
    NotepadOutput._add_highlight(widget, (2, 0))
    assert widget._highlights == []
    widget.schedule_save.assert_not_called()


def test_remove_range_from_highlights_splits_existing_range():
    widget = SimpleNamespace(
        _highlights=[(0, 10), (20, 5)],
        _sanitize_ranges=lambda ranges: NotepadOutput._sanitize_ranges(SimpleNamespace(), ranges),
        _merge_ranges=lambda ranges: NotepadOutput._merge_ranges(SimpleNamespace(), ranges),
        schedule_save=MagicMock(),
    )
    NotepadOutput._remove_range_from_highlights(widget, 3, 4)
    assert widget._highlights == [(0, 3), (7, 3), (20, 5)]
    widget.schedule_save.assert_called_once_with()


def test_remove_range_from_highlights_handles_full_and_non_overlapping_subtractions():
    helper = SimpleNamespace()
    widget = SimpleNamespace(
        _highlights=[(5, 5)],
        _sanitize_ranges=lambda ranges: NotepadOutput._sanitize_ranges(helper, ranges),
        _merge_ranges=lambda ranges: NotepadOutput._merge_ranges(helper, ranges),
        schedule_save=MagicMock(),
    )
    NotepadOutput._remove_range_from_highlights(widget, 0, 20)
    assert widget._highlights == []

    widget._highlights = [(5, 5)]
    widget.schedule_save.reset_mock()
    NotepadOutput._remove_range_from_highlights(widget, 20, 2)
    assert widget._highlights == [(5, 5)]
    widget.schedule_save.assert_called_once_with()


def test_remove_range_ignores_non_positive_length():
    widget = SimpleNamespace(_highlights=[(0, 3)], schedule_save=MagicMock())
    NotepadOutput._remove_range_from_highlights(widget, 1, 0)
    assert widget._highlights == [(0, 3)]
    widget.schedule_save.assert_not_called()


def test_selection_overlap_detects_any_intersection():
    widget = SimpleNamespace(_highlights=[(0, 5), (10, 3)])
    assert NotepadOutput._selection_overlaps_any_highlight(widget, 4, 6) is True
    assert NotepadOutput._selection_overlaps_any_highlight(widget, 5, 10) is False
    assert NotepadOutput._selection_overlaps_any_highlight(widget, 11, 12) is True


def test_persist_stops_timer_and_saves_current_notepad():
    timer = MagicMock()
    timer.isActive.return_value = True
    controller = SimpleNamespace(notepad=SimpleNamespace(save=MagicMock()))
    widget = SimpleNamespace(_save_timer=timer, window=SimpleNamespace(controller=controller), id="note-1")
    NotepadOutput._persist(widget)
    timer.stop.assert_called_once_with()
    controller.notepad.save.assert_called_once_with("note-1")


def test_apply_highlight_theme_is_fail_safe():
    highlighter = MagicMock()
    widget = SimpleNamespace(_highlighter=highlighter)
    NotepadOutput.apply_highlight_theme(widget)
    highlighter.rehighlight.assert_called_once_with()

    highlighter.rehighlight.side_effect = RuntimeError("gone")
    NotepadOutput.apply_highlight_theme(widget)


def test_dark_theme_delegates_to_theme_controller():
    theme = SimpleNamespace(is_dark_theme=MagicMock(return_value=True))
    widget = SimpleNamespace(window=SimpleNamespace(controller=SimpleNamespace(theme=theme)))
    assert NotepadOutput._is_dark_theme(widget) is True
    theme.is_dark_theme.assert_called_once_with()
