from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QTextCursor

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


@pytest.fixture
def editor(qapp):
    window = QWidget()
    window.core = MagicMock()
    window.controller = MagicMock()
    window.core.config.data = {'font_size': 12}
    window.core.config.get.return_value = 12
    window.core.notepad.locked = False
    widget = NotepadOutput(window)
    widget.setPlainText('0123456789abcdefghij01234')
    yield widget
    widget._save_timer.stop()
    window.deleteLater()
    qapp.processEvents()


def edit(editor, start, end, text=''):
    cursor = editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    cursor.insertText(text)
    editor.setTextCursor(cursor)


def test_mark_and_unmark_merge_split_and_undo(editor):
    editor.set_highlights([(0, 3)])
    editor._add_highlight((2, 5))
    assert editor.get_highlights() == [(0, 7)]
    editor._remove_range_from_highlights(3, 2)
    assert editor.get_highlights() == [(0, 3), (5, 2)]
    editor.undo()
    assert editor.get_highlights() == [(0, 7)]
    editor.undo()
    assert editor.get_highlights() == [(0, 3)]


def test_zero_length_marking_does_not_change_ranges(editor):
    editor.set_highlights([(0, 3)])
    editor._add_highlight((2, 0))
    editor._remove_range_from_highlights(1, 0)
    assert editor.get_highlights() == [(0, 3)]


def test_selection_overlap_detects_any_intersection(editor):
    editor.set_highlights([(0, 5), (10, 3)])
    assert editor._selection_overlaps_any_highlight(4, 6)
    assert not editor._selection_overlaps_any_highlight(5, 10)
    assert editor._selection_overlaps_any_highlight(11, 12)


@pytest.mark.parametrize('start,end,text,expected', [
    (0, 0, 'abc', [(8, 5)]),
    (0, 3, '', [(2, 5)]),
    (7, 7, 'abc', [(5, 8)]),
    (7, 9, '', [(5, 3)]),
    (3, 7, '', [(3, 3)]),
    (8, 12, '', [(5, 3)]),
    (4, 11, '', []),
    (12, 14, 'abc', [(5, 5)]),
    (6, 9, 'abcde', [(5, 7)]),
])
def test_markers_follow_edits_and_undo_redo(editor, start, end, text, expected):
    editor.set_highlights([(5, 5)])
    original = editor.toPlainText()
    edit(editor, start, end, text)
    assert editor.get_highlights() == expected
    editor.undo()
    assert editor.toPlainText() == original
    assert editor.get_highlights() == [(5, 5)]
    editor.redo()
    assert editor.get_highlights() == expected


def test_delete_everything_then_undo_restores_markers(editor, qapp):
    editor.set_highlights([(5, 5)])
    edit(editor, 0, len(editor.toPlainText()))
    assert editor.get_highlights() == []
    editor.undo()
    qapp.processEvents()  # no queued clear is allowed to wipe restored markers
    assert editor.get_highlights() == [(5, 5)]
    editor.redo()
    edit(editor, 0, 0, 'new text')
    assert editor.get_highlights() == []


def test_multiline_unicode_markers_survive_serialization_and_render_full_characters(editor):
    editor.setPlainText('a😀b\nc😀d\nend')
    editor.set_highlights([(1, 9)])
    assert editor.get_highlights() == [(1, 9)]
    edit(editor, 0, 0, '😀\n')
    assert editor.get_highlights() == [(4, 9)]
    saved_text, saved_ranges = editor.toPlainText(), editor.get_highlights()
    editor.setPlainText(saved_text)
    editor.set_highlights(saved_ranges)
    assert editor.get_highlights() == saved_ranges
    editor._highlighter.rehighlight()
    block = editor.document().findBlock(4)
    formats = block.layout().formats()
    assert any(fmt.start == 1 and fmt.length == 3 for fmt in formats)


def test_restored_markers_are_not_a_separate_undo_step(editor):
    editor.set_highlights([(5, 5)])
    assert not editor.document().isUndoAvailable()
    editor.clear_highlights()
    assert editor.get_highlights() == []
    editor.undo()
    assert editor.get_highlights() == [(5, 5)]


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
