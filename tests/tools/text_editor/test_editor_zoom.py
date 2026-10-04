"""Zoom should touch editor layout, never rebuild the application or its content."""
from types import SimpleNamespace
from unittest.mock import MagicMock
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget
from pygpt_net.tools.text_editor.ui.widgets import TextFileEditor
from pygpt_net.tools.web_browser.ui.widgets import SourceEditor
from pygpt_net.tools.files.ui.preview.text import TextPreview


def test_shared_zoom_coalesces_layout_and_preserves_content(qapp, monkeypatch, tmp_path):
    from pygpt_net.core.text.editor import base, syntax
    window = QWidget()
    values = {'font_size': 14, 'filesystem.preview.text.font_size': 13}
    config = MagicMock()
    config.get.side_effect = values.get
    config.set.side_effect = values.__setitem__
    window.core = SimpleNamespace(config=config)
    window.controller = MagicMock()
    window.ui = SimpleNamespace(nodes={})
    panel = QWidget(window)
    panel.window = window
    editor = TextFileEditor(window)
    source = SourceEditor(SimpleNamespace(window=window), window)
    preview = TextPreview(panel, str(tmp_path / 'large.py'), 'value = 42\n' * 1200)
    editor.setPlainText('example\n' * 1200)
    source.setPlainText('<p>example</p>\n' * 1200)
    QTest.qWait(250)
    lex = MagicMock(wraps=syntax.lex)
    monkeypatch.setattr(syntax, 'lex', lex)
    font = MagicMock(wraps=base.local_font)
    monkeypatch.setattr(base, 'local_font', font)
    cursor = source.textCursor()
    cursor.setPosition(3)
    cursor.setPosition(9, QTextCursor.KeepAnchor)
    source.setTextCursor(cursor)
    before = source.toPlainText()
    undo_available = source.document().isUndoAvailable()
    modified = source.document().isModified()
    try:
        for size in range(15, 25):
            source.on_zoom_changed(size)
        font.assert_not_called()
        QTest.qWait(60)
        assert font.call_count == 1
        assert source._applied_zoom == 24
        config.save.assert_not_called()
        window._text_zoom_commit.flush()
        config.save.assert_called_once()
        window.controller.theme.nodes.apply_all.assert_not_called()
        assert editor.value == 24
        assert preview.value == 13
        assert source.toPlainText() == before
        assert source.textCursor().selectedText() == before[3:9]
        assert source.document().isModified() == modified
        assert source.document().isUndoAvailable() == undo_available
        QTest.qWait(220)
        lex.assert_not_called()
        font.reset_mock()
        for size in range(14, 23):
            preview.on_zoom_changed(size)
        QTest.qWait(60)
        assert font.call_count == 1
        window._text_zoom_commit.flush()
        assert preview.value == 22 and source.value == 24
        window.controller.theme.nodes.apply_all.assert_not_called()
    finally:
        for widget in (editor, source, preview):
            widget.on_destroy()
        window._text_zoom_commit.timer.stop()
        window.deleteLater()
