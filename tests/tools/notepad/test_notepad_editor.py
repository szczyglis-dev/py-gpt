from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QTextCursor

from pygpt_net.tools.notepad.ui.editor import NotepadOutput
from pygpt_net.tools.notepad.ui.widget import NotepadWidget
from pygpt_net.tools.notepad.core.markers import Markers


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
    assert Markers.sanitize(widget, ranges) == [(3, 2), (5, 2)]
    assert Markers.sanitize(widget, None) == []


def test_merge_ranges_merges_overlapping_and_adjacent_ranges():
    widget = SimpleNamespace()
    assert Markers.merge(widget, []) == []
    assert Markers.merge(widget, [(0, 3), (3, 2), (10, 2), (11, 4)]) == [
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
    session = SimpleNamespace(loading=False, save=MagicMock())
    widget = NotepadOutput(session, window)
    widget.setPlainText('0123456789abcdefghij01234')
    yield widget
    widget.save_timer.stop()
    window.deleteLater()


def edit(editor, start, end, text=''):
    cursor = editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    cursor.insertText(text)
    editor.setTextCursor(cursor)


def test_mark_and_unmark_merge_split_and_undo(editor):
    editor.markers.restore([(0, 3)])
    editor.markers.add((2, 5))
    assert editor.markers.ranges() == [(0, 7)]
    editor.markers.remove(3, 2)
    assert editor.markers.ranges() == [(0, 3), (5, 2)]
    editor.undo()
    assert editor.markers.ranges() == [(0, 7)]
    editor.undo()
    assert editor.markers.ranges() == [(0, 3)]


def test_zero_length_marking_does_not_change_ranges(editor):
    editor.markers.restore([(0, 3)])
    editor.markers.add((2, 0))
    editor.markers.remove(1, 0)
    assert editor.markers.ranges() == [(0, 3)]


def test_selection_overlap_detects_any_intersection(editor):
    editor.markers.restore([(0, 5), (10, 3)])
    assert editor.markers.overlaps(4, 6)
    assert not editor.markers.overlaps(5, 10)
    assert editor.markers.overlaps(11, 12)


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
    editor.markers.restore([(5, 5)])
    original = editor.toPlainText()
    edit(editor, start, end, text)
    assert editor.markers.ranges() == expected
    editor.undo()
    assert editor.toPlainText() == original
    assert editor.markers.ranges() == [(5, 5)]
    editor.redo()
    assert editor.markers.ranges() == expected


def test_delete_everything_then_undo_restores_markers(editor, qapp):
    editor.markers.restore([(5, 5)])
    edit(editor, 0, len(editor.toPlainText()))
    assert editor.markers.ranges() == []
    editor.undo()
    assert editor.markers.ranges() == [(5, 5)]
    editor.redo()
    edit(editor, 0, 0, 'new text')
    assert editor.markers.ranges() == []


def test_multiline_unicode_markers_survive_serialization_and_render_full_characters(editor):
    editor.setPlainText('a😀b\nc😀d\nend')
    editor.markers.restore([(1, 9)])
    assert editor.markers.ranges() == [(1, 9)]
    edit(editor, 0, 0, '😀\n')
    assert editor.markers.ranges() == [(4, 9)]
    saved_text, saved_ranges = editor.toPlainText(), editor.markers.ranges()
    editor.setPlainText(saved_text)
    editor.markers.restore(saved_ranges)
    assert editor.markers.ranges() == saved_ranges
    editor.markers.highlighter.rehighlight()
    block = editor.document().findBlock(4)
    formats = block.layout().formats()
    assert any(fmt.start == 1 and fmt.length == 3 for fmt in formats)


def test_restored_markers_are_not_a_separate_undo_step(editor):
    editor.markers.restore([(5, 5)])
    assert not editor.document().isUndoAvailable()
    editor.markers.clear()
    assert editor.markers.ranges() == []
    editor.undo()
    assert editor.markers.ranges() == [(5, 5)]


def test_persist_stops_timer_and_saves_current_notepad():
    timer = MagicMock()
    timer.isActive.return_value = True
    session = SimpleNamespace(save=MagicMock())
    widget = SimpleNamespace(save_timer=timer, session=session)
    NotepadOutput.persist(widget)
    timer.stop.assert_called_once_with()
    session.save.assert_called_once_with()


def test_apply_highlight_theme_is_fail_safe():
    highlighter = MagicMock()
    widget = SimpleNamespace(highlighter=highlighter)
    Markers.apply_theme(widget)
    highlighter.rehighlight.assert_called_once_with()

    highlighter.rehighlight.side_effect = RuntimeError("gone")
    Markers.apply_theme(widget)


def test_dark_theme_delegates_to_theme_controller():
    theme = SimpleNamespace(is_dark_theme=MagicMock(return_value=True))
    widget = SimpleNamespace(editor=SimpleNamespace(window=SimpleNamespace(controller=SimpleNamespace(theme=theme))))
    assert Markers.is_dark(widget) is True
    theme.is_dark_theme.assert_called_once_with()
