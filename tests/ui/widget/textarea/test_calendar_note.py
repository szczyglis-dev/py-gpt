from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.textarea.calendar_note import CalendarNote


def _note():
    config = SimpleNamespace(data={"font_size": 12}, save=MagicMock())
    return SimpleNamespace(
        window=SimpleNamespace(
            core=SimpleNamespace(config=config),
            controller=SimpleNamespace(
                calendar=SimpleNamespace(note=MagicMock()), finder=MagicMock(), audio=MagicMock(),
                settings=SimpleNamespace(editor=MagicMock()), config=MagicMock(), ui=MagicMock(),
            ),
        ),
        finder=MagicMock(), tab=None, value=12, min_font_size=8, max_font_size=42,
        find_open=MagicMock(), textCursor=MagicMock(),
    )


def test_set_tab_and_text_changed_delegate():
    n = _note()
    tab = object()
    CalendarNote.set_tab(n, tab)
    assert n.tab is tab
    CalendarNote.text_changed(n)
    n.window.controller.calendar.note.update.assert_called_once_with()
    n.finder.text_changed.assert_called_once_with()


def test_audio_read_selection_and_find_open():
    n = _note()
    n.textCursor.return_value.selectedText.return_value = "hello"
    CalendarNote.audio_read_selection(n)
    n.window.controller.audio.read_text.assert_called_once_with("hello")
    CalendarNote.find_open(n)
    n.window.controller.finder.open.assert_called_once_with(n.finder)


def test_on_update_clears_finder():
    n = _note()
    CalendarNote.on_update(n)
    n.finder.clear.assert_called_once_with()


def test_ctrl_wheel_uses_shared_zoom_scheduler(monkeypatch):
    n = _note()
    zoom = MagicMock()
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.calendar_note.zoom_text', zoom)
    event = MagicMock()
    event.modifiers.return_value = Qt.ControlModifier
    event.angleDelta.return_value.y.return_value = 120
    CalendarNote.wheelEvent(n, event)
    zoom.assert_called_once_with(n, n.window, 13, 'font_size')
    n.window.core.config.save.assert_not_called()
    event.accept.assert_called_once_with()


def test_ctrl_wheel_respects_font_size_bounds():
    n = _note()
    n.value = n.max_font_size
    n.window.controller.settings.editor.get_option.return_value = {"value": 0}
    event = MagicMock()
    event.modifiers.return_value = Qt.ControlModifier
    event.angleDelta.return_value.y.return_value = 120
    CalendarNote.wheelEvent(n, event)
    assert n.value == n.max_font_size
