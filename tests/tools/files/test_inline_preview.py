from types import SimpleNamespace
import threading
from unittest.mock import MagicMock

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from pygpt_net.tools.files.ui.explorer import FileExplorer
from pygpt_net.tools.files.ui.preview import PreviewPanel
from pygpt_net.tools.files.ui.preview.readers import ReaderRegistry, TextReader
from pygpt_net.tools.files.ui.preview.text import TextPreview
from pygpt_net.tools.files.ui.search import find_paths


@pytest.fixture
def app(monkeypatch, qt_application):
    for module in ('pygpt_net.tools.files.ui.preview',
                   'pygpt_net.tools.files.ui.preview.media',
                   'pygpt_net.tools.files.ui.search',
                   'pygpt_net.tools.files.ui.explorer'):
        monkeypatch.setattr(module + '.trans', lambda key: key)
    return qt_application


def test_recursive_search_keeps_only_matches_and_ancestors(tmp_path):
    (tmp_path / 'a' / 'deep').mkdir(parents=True)
    (tmp_path / 'empty').mkdir()
    match = tmp_path / 'a' / 'deep' / 'HELLO.txt'
    match.write_text('hello')
    (tmp_path / 'a' / 'no.png').write_bytes(b'png')
    accepted, dirs = find_paths(str(tmp_path), '*.txt')
    assert accepted == {str(tmp_path), str(tmp_path / 'a'), str(match.parent), str(match)}
    assert dirs == accepted - {str(match)}
    assert find_paths(str(tmp_path), 'hello')[0] == accepted
    assert find_paths(str(tmp_path), 'a/deep/*.txt')[0] == accepted
    cancelled = threading.Event()
    cancelled.set()
    assert find_paths(str(tmp_path), '*', cancelled) is None


def test_readers_detect_binary_utf16_and_extensionless(tmp_path):
    path = tmp_path / 'README'
    path.write_text('hello')
    assert ReaderRegistry().resolve(str(path)).kind == 'text'
    path.write_bytes('Zażółć'.encode('utf-16'))
    assert TextReader().read(path) == ('Zażółć', 'utf-16')
    path.write_bytes(b'\x00binary')
    assert ReaderRegistry().resolve(str(path)) is None
    path.write_bytes(b'x' * (TextReader.max_bytes + 1))
    assert ReaderRegistry().resolve(str(path)) is None


def test_panel_edit_save_and_conflict(app, tmp_path, monkeypatch):
    file = tmp_path / 'test.py'
    file.write_bytes(b'print("hello")\r\n')
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    assert panel.open_file(str(file))
    assert isinstance(panel.viewer, TextPreview)
    panel.viewer.setPlainText('print("changed")\n')
    assert panel.save()
    assert file.read_bytes() == b'print("changed")\r\n'
    file.write_text('external change')
    warning = MagicMock()
    monkeypatch.setattr(QMessageBox, 'warning', warning)
    assert not panel.save()
    assert file.read_text() == 'external change'
    assert warning.called
    target = tmp_path / 'copy.py'
    assert panel.save(str(target))
    assert target.read_bytes() == b'print("changed")\r\n'
    panel.deleteLater()



def test_unsaved_cancel_preserves_view(app, tmp_path, monkeypatch):
    a, b = tmp_path / 'a.txt', tmp_path / 'b.txt'
    a.write_text('a')
    b.write_text('b')
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    panel.open_file(str(a))
    panel.viewer.insertPlainText('changed')
    monkeypatch.setattr(QMessageBox, 'question', lambda *_: QMessageBox.Cancel)
    assert panel.open_file(str(b)) is False
    assert panel.path == str(a)
    panel.deleteLater()



def test_image_and_unsupported_dispatch(app, tmp_path):
    image = QImage(20, 20, QImage.Format_RGB32)
    image.fill(0xff123456)
    path = tmp_path / 'image.png'
    image.save(str(path))
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    panel.open_file(str(path))
    assert panel.viewer.scene().items()
    binary = tmp_path / 'unknown.bin'
    binary.write_bytes(b'\x00binary')
    panel.open_file(str(binary))
    assert not isinstance(panel.viewer, TextPreview)
    assert panel.path == str(binary)
    panel.deleteLater()



def test_audio_preview_loads_and_releases_source(app, tmp_path, monkeypatch):
    import wave
    import PySide6.QtMultimedia as multimedia
    import PySide6.QtMultimediaWidgets as multimedia_widgets
    # Isolate system audio services: the offscreen sandbox has no PulseAudio access.
    player = MagicMock()
    player.playbackState.return_value = multimedia.QMediaPlayer.StoppedState
    factory = MagicMock(return_value=player)
    factory.PlayingState = multimedia.QMediaPlayer.PlayingState
    monkeypatch.setattr(multimedia, 'QMediaPlayer', factory)
    monkeypatch.setattr(multimedia, 'QAudioOutput', MagicMock())
    monkeypatch.setattr(multimedia_widgets, 'QVideoWidget', QWidget)
    from pygpt_net.tools.files.ui.preview.media import MediaPreview
    audio = tmp_path / 'sample.wav'
    with wave.open(str(audio), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b'\x00\x00' * 800)
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    panel.open_file(str(audio))
    assert isinstance(panel.viewer, MediaPreview)
    player = panel.viewer.player
    assert player.setSource.call_args.args[0].toLocalFile() == str(audio)
    panel.viewer.play.click()
    player.play.assert_called_once()
    panel.show_empty()
    assert player.setSource.call_args.args[0].isEmpty()
    player.stop.assert_called_once()
    panel.deleteLater()



def test_file_preview_and_breadcrumbs_route_to_selected_path(app, tmp_path):
    from PySide6.QtWidgets import QPushButton
    folder = tmp_path / 'sub'
    folder.mkdir()
    path = folder / 'test.py'
    path.write_text('print(1)')
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    assert panel.open_file(str(path))
    assert panel.path == str(path)
    buttons = panel.breadcrumbs_widget.findChildren(QPushButton)
    assert any(button.toolTip() == '.' for button in buttons)
    assert any(button.toolTip() == 'sub' for button in buttons)
    panel.show_empty()
    panel.deleteLater()


def test_zoom_uses_shared_config_and_ctrl_wheel(app, tmp_path):
    from PySide6.QtCore import Qt, QPoint
    window = MagicMock()
    values = {'font_size': 16}
    window.core.config.get.side_effect = values.get
    window.core.config.set.side_effect = values.__setitem__
    panel = PreviewPanel(window, str(tmp_path))
    path = tmp_path / 'zoom.txt'
    path.write_text('text')
    panel.open_file(str(path))
    assert panel.viewer.value == 16
    event = MagicMock()
    event.modifiers.return_value = Qt.ControlModifier
    event.angleDelta.return_value = QPoint(0, 120)
    panel.viewer.wheelEvent(event)
    assert panel.viewer.value == 17
    assert values['filesystem.preview.text.font_size'] == 17
    assert values['font_size'] == 16
    window.core.config.save.assert_not_called()
    window._text_zoom_commit.flush()
    window.core.config.save.assert_called_once()
    event.accept.assert_called_once()
    panel.show_empty()
    panel.open_file(str(path))
    assert panel.viewer.value == 17
    panel.deleteLater()



def test_dark_highlighting_is_correct_on_show_and_theme_change(app, tmp_path):
    from pygments.token import Name
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    panel.setStyleSheet('QPlainTextEdit { background: #202020; color: #eeeeee; }')
    path = tmp_path / 'colors.py'
    path.write_text('def example():\n    return 1\n')
    panel.open_file(str(path))
    panel.viewer.ensurePolished()
    panel.viewer.highlighter.timer.stop()
    panel.viewer.highlighter.refresh()
    color = panel.viewer.highlighter.formats[Name.Function].foreground().color()
    assert color.name() == '#aaa0c7'
    panel.setStyleSheet('QPlainTextEdit { background: #ffffff; color: #202020; }')
    panel.viewer.ensurePolished()
    panel.viewer.highlighter.timer.stop()
    panel.viewer.highlighter.refresh()
    color = panel.viewer.highlighter.formats[Name.Function].foreground().color()
    assert color.name() == '#6e6693'
    panel.close()
    panel.deleteLater()



def test_directory_search_exposes_subtree_without_expanding_descendants(tmp_path):
    folder = tmp_path / 'reports'
    nested = folder / 'child'
    nested.mkdir(parents=True)
    (folder / 'summary.txt').write_text('hello')
    (nested / 'hidden.txt').write_text('deep')
    accepted, expanded = find_paths(str(tmp_path), 'reports')
    assert str(folder) in expanded
    assert str(nested) in accepted
    assert str(nested) not in expanded
    assert str(folder / 'summary.txt') in accepted
    assert str(nested / 'hidden.txt') in accepted


def test_preview_uses_shared_finder_and_cleans_up(app, tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    window = MagicMock()
    panel = PreviewPanel(window, str(tmp_path))
    path = tmp_path / 'search.txt'
    path.write_text('needle and needle')
    panel.open_file(str(path))
    editor = panel.viewer
    QTest.keyClick(editor, Qt.Key_F, Qt.ControlModifier)
    window.controller.finder.open.assert_called_once_with(editor.finder)
    editor.finder.find('needle')
    editor.finder.timer.stop()
    editor.finder.find_execute()
    assert len(editor.finder.matches) == 2
    panel.show_empty()
    window.controller.finder.unset.assert_called_with(editor.finder)
    assert editor.finder.parent() is None
    panel.deleteLater()



def test_zoom_burst_saves_once_without_relexing(app, tmp_path, monkeypatch):
    from pygpt_net.core.text.editor import syntax as syntax_module
    window = MagicMock()
    values = {'font_size': 12}
    window.core.config.get.side_effect = values.get
    window.core.config.set.side_effect = values.__setitem__
    panel = PreviewPanel(window, str(tmp_path))
    path = tmp_path / 'zoom.py'
    path.write_text('def example():\n    return 1\n')
    panel.open_file(str(path))
    panel.viewer.highlighter.timer.stop()
    panel.viewer.highlighter.refresh()
    lex = MagicMock(wraps=syntax_module.lex)
    monkeypatch.setattr(syntax_module, 'lex', lex)
    for value in range(13, 20):
        panel.viewer.on_zoom_changed(value)

    assert panel.viewer.value == 19
    window.core.config.save.assert_not_called()
    window._text_zoom_commit.flush()
    window.core.config.save.assert_called_once()
    window.controller.theme.nodes.apply_all.assert_not_called()
    window.controller.config.apply.assert_not_called()
    lex.assert_not_called()
    panel.close()
    panel.deleteLater()



def test_gutter_tracks_lines_zoom_and_keeps_finder_highlights(app, tmp_path):
    from PySide6.QtGui import QTextCursor
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    path = tmp_path / 'lines.txt'
    path.write_text('\n'.join(['needle'] * 9))
    panel.open_file(str(path))

    editor = panel.viewer
    width = editor.line_numbers.width()
    editor.appendPlainText('line ten')
    assert editor.line_numbers.width() > width
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.finder.find('needle')
    # Execute the pending search deterministically rather than racing the Qt timer.
    editor.finder.timer.stop()
    editor.finder.find_execute()
    assert len(editor.extraSelections()) == 9  # only search matches highlight the code
    editor.finder.clear_search()
    assert editor.extraSelections() == []
    width = editor.line_numbers.width()
    editor.on_zoom_changed(30)
    editor.zoom_timer.stop()
    editor.zoom_timer.timeout.emit()

    assert editor.line_numbers.width() > width
    panel.close()
    panel.deleteLater()



def test_file_annotation_popup_captures_relative_path_and_selected_lines(app, tmp_path, monkeypatch):
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QDialog, QPlainTextEdit
    from pygpt_net.ui.widget.textarea.annotations import ChatAnnotations
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.text.trans', lambda key, **kwargs: key)
    window = MagicMock()
    window.core.filesystem.get_data_dir.return_value = str(tmp_path)
    session = ChatAnnotations(window, 1)
    window.controller.chat.text.get_annotations.return_value = session
    folder = tmp_path / 'nested'
    folder.mkdir()
    path = folder / 'example.txt'
    path.write_text('first\nZażółć 😀\nthird')
    panel = PreviewPanel(window, str(folder))
    panel.open_file(str(path))
    editor = panel.viewer
    cursor = editor.textCursor()
    cursor.setPosition(6)
    cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)

    def accept(dialog):
        dialog.findChild(QPlainTextEdit).setPlainText('Popraw tę linię')
        return QDialog.Accepted

    monkeypatch.setattr(QDialog, 'exec', accept)
    editor.annotate(cursor)
    item = session.annotations[0]
    assert item['path'] == 'nested/example.txt'  # relative to workdir, not browsed folder
    assert (item['start_line'], item['end_line']) == (2, 2)
    assert item['selection'] == 'Zażółć 😀\n'
    panel.show_empty()
    assert 'Popraw tę linię' in session.prompt_block()
    assert 'nested/example.txt' in session.prompt_block()
    panel.deleteLater()



def test_line_number_spacing_and_font_are_configurable(app, tmp_path, monkeypatch):
    from PySide6.QtGui import QFontMetrics
    from pygpt_net.core.text.editor import base as base_module
    from pygpt_net.core.text.editor import gutter as gutter_module
    monkeypatch.setattr(base_module, 'LINE_NUMBER_PADDING', 13)
    monkeypatch.setattr(base_module, 'LINE_NUMBER_TEXT_GAP', 5)
    monkeypatch.setattr(gutter_module, 'LINE_NUMBER_PADDING', 13)
    monkeypatch.setattr(gutter_module, 'LINE_NUMBER_FONT_SCALE', 0.75)
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    path = tmp_path / 'padding.txt'
    path.write_text('code')
    panel.open_file(str(path))
    editor = panel.viewer
    font = editor.line_numbers.number_font()
    assert QFontMetrics(font).height() < editor.fontMetrics().height()
    assert editor.line_numbers.width() == 26 + QFontMetrics(font).horizontalAdvance('9')
    assert editor.viewportMargins().left() == editor.line_numbers.width() + 5
    panel.deleteLater()



def test_annotation_gutter_follows_add_remove_delivery_and_conversation(app, tmp_path, monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.annotations.trans', lambda key, **kwargs: key)
    from pygpt_net.ui.widget.textarea.annotations import ChatAnnotations, clear_sent_annotations
    from pygpt_net.item.ctx import CtxItem
    window = MagicMock()
    window.core.filesystem.get_data_dir.return_value = str(tmp_path)
    session = ChatAnnotations(window, 1)
    window.controller.chat.text.get_annotations.return_value = session
    path = tmp_path / 'notes.txt'
    path.write_text('one\ntwo\nthree')
    panel = PreviewPanel(window, str(tmp_path))
    panel.open_file(str(path))
    editor = panel.viewer
    session.add_file_annotation('other.txt', 1, 3, 'other', 'ignore')
    item = session.add_file_annotation('notes.txt', 1, 2, 'one\ntwo', 'fix')
    editor.refresh_annotations()
    assert editor.annotation_ranges == ((1, 2),)
    session._remove_annotation(item['id'])
    editor.refresh_annotations()
    assert editor.annotation_ranges == ()
    session.add_file_annotation('notes.txt', 2, 3, 'two\nthree', 'fix')
    editor.refresh_annotations()
    assert editor.annotation_ranges == ((2, 3),)
    ctx = CtxItem()
    session.prompt_block(ctx)
    clear_sent_annotations(ctx)
    editor.refresh_annotations()
    assert editor.annotation_ranges == ()
    session.add_file_annotation('notes.txt', 1, 1, 'one', 'keep')
    editor.refresh_annotations()
    assert editor.annotation_ranges == ((1, 1),)
    window.controller.chat.text.get_annotations.return_value = ChatAnnotations(window, 2)
    editor.refresh_annotations()
    assert editor.annotation_ranges == ()
    panel.show_empty()
    assert not editor.annotation_timer.isActive()
    panel.close()
    panel.deleteLater()



@pytest.mark.parametrize('ending', [b'\r\n', b'\r', b'\n'])
def test_csv_load_normalization_is_not_an_edit(app, tmp_path, monkeypatch, ending):
    csv = tmp_path / 'table.csv'
    original = ending.join([b'name,value', b'first,1', b'second,2', b''])
    csv.write_bytes(original)
    other = tmp_path / 'other.txt'
    other.write_text('other file')
    panel = PreviewPanel(MagicMock(), str(tmp_path))
    question = MagicMock(return_value=QMessageBox.Cancel)
    monkeypatch.setattr(QMessageBox, 'question', question)
    assert panel.open_file(str(csv))
    assert not panel.viewer.is_content_modified()
    panel.viewer.document().setModified(True)  # formatting-only changes
    assert panel.open_file(str(other))
    question.assert_not_called()
    assert csv.read_bytes() == original
    assert panel.open_file(str(csv))
    panel.viewer.insertPlainText('edited')
    assert panel.viewer.is_content_modified()
    assert not panel.open_file(str(other))
    question.assert_called_once()
    panel.viewer.undo()
    assert not panel.viewer.is_content_modified()
    assert panel.open_file(str(other))
    panel.deleteLater()
