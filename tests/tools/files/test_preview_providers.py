from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QLabel, QWidget

from pygpt_net.core.file_preview import FilePreviews
from pygpt_net.provider.file_preview import BaseFilePreview
from pygpt_net.tools.files.ui.preview import PreviewPanel
from pygpt_net.tools.files.ui.preview.markdown import MarkdownPreview
from pygpt_net.core.extensions.extensions import Extensions


class Preview(BaseFilePreview):
    id = 'test'
    extensions = ('.JSON',)

    def __init__(self):
        super().__init__()
        self.released = []

    def create_widget(self, path, parent):
        return QLabel('external preview', parent)

    def release_widget(self, widget):
        self.released.append(widget)


def test_preview_addon_type_and_priority():
    manager = FilePreviews()
    one, two = Preview(), Preview()
    two.id = 'second'
    manager.register(one)
    manager.register(two)
    assert manager.resolve('/work/sample.json') is two
    manager.unregister('second')
    assert manager.resolve('/work/sample.JSON') is one
    assert manager.resolve('/work/sample.txt') is None
    assert Extensions.normalize_type('file_previews') == 'file_preview'
    Extensions._validate_runtime_objects('file_preview', [one])


def test_live_registry_and_cleanup(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    window = SimpleNamespace(core=SimpleNamespace(file_previews=FilePreviews()))
    panel = PreviewPanel(window, str(tmp_path))
    provider = Preview()
    window.core.file_previews.register(provider)
    path = tmp_path / 'data.json'
    path.write_text('{}')
    panel.open_file(str(path))
    viewer = panel.viewer
    assert isinstance(viewer, QLabel)
    assert viewer.parentWidget() is panel
    panel.show_empty()
    assert provider.released == [viewer]
    provider.create_widget = MagicMock(side_effect=RuntimeError('broken add-on'))
    panel.open_file(str(path))
    assert panel.viewer.findChildren(QLabel)[-1].text().endswith('broken add-on')
    panel.deleteLater()


def test_builtin_markdown_renders_and_resolves_local_links(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    panel = PreviewPanel(SimpleNamespace(), str(tmp_path))
    path = tmp_path / 'README.md'
    path.write_text('# Heading\n\n**Bold** and [next](next.md)\n\n- Item')
    panel.open_file(str(path))
    assert isinstance(panel.viewer, MarkdownPreview)
    assert '# Heading' not in panel.viewer.toPlainText()
    assert 'Heading' in panel.viewer.toPlainText()
    assert 'font-weight' in panel.viewer.toHtml()
    assert panel.viewer.document().baseUrl().toLocalFile() == str(tmp_path) + '/'
    assert panel.viewer.isReadOnly()
    panel.deleteLater()


def test_panel_deletion_releases_external_widget(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    manager = FilePreviews()
    provider = Preview()
    manager.register(provider)
    panel = PreviewPanel(SimpleNamespace(core=SimpleNamespace(file_previews=manager)), str(tmp_path))
    path = tmp_path / 'data.json'
    path.write_text('{}')
    panel.open_file(str(path))
    viewer = panel.viewer
    panel.deleteLater()
    QCoreApplication.sendPostedEvents(panel, QEvent.DeferredDelete)
    assert provider.released == [viewer]


def test_markdown_source_round_trip_and_cancel(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox, QMenu
    from pygpt_net.tools.files.ui.preview.text import TextPreview
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    window = MagicMock()
    window.core.config.get.return_value = 12
    window.core.config.data = {'font_size': 12}
    panel = PreviewPanel(window, str(tmp_path))
    path = tmp_path / 'sample.md'
    path.write_bytes(b'# Original\r\n')
    panel.open_file(str(path))
    menu = QMenu()
    panel.add_file_actions(menu)
    assert menu.actions()[0].text() == 'files.preview.edit_source'
    panel.edit_markdown_source()
    assert isinstance(panel.viewer, TextPreview)
    panel.viewer.setPlainText('# Updated\n')
    question = MagicMock(return_value=QMessageBox.Cancel)
    monkeypatch.setattr(QMessageBox, 'question', question)
    panel.back_to_markdown_preview()
    assert isinstance(panel.viewer, TextPreview)
    assert panel.viewer.is_content_modified()
    question.return_value = QMessageBox.Save
    panel.back_to_markdown_preview()
    assert isinstance(panel.viewer, MarkdownPreview)
    assert panel.viewer.toPlainText() == 'Updated'
    assert path.read_bytes() == b'# Updated\r\n'
    panel.edit_markdown_source()
    panel.viewer.setPlainText('# Discarded')
    question.reset_mock()
    question.return_value = QMessageBox.Discard
    panel.back_to_markdown_preview()
    question.assert_called_once()
    assert panel.viewer.toPlainText() == 'Updated'
    panel.deleteLater()


def test_markdown_link_colors_and_ctrl_wheel(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt, QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    window = MagicMock()
    panel = PreviewPanel(window, str(tmp_path))
    path = tmp_path / 'links.md'
    path.write_text('[Link](https://example.com)')
    for theme, color in [('dark', '#80caff'), ('light', '#154c96')]:
        window.controller.theme.common.get_theme_type.return_value = theme
        viewer = MarkdownPreview(str(path), panel)
        fragment = viewer.document().begin().begin().fragment()
        assert fragment.charFormat().foreground().color().name() == color
        size = viewer.document().defaultFont().pointSizeF()
        for delta, expected in [(120, size + 1), (-120, size)]:
            event = QWheelEvent(QPointF(), QPointF(), QPoint(), QPoint(0, delta),
                                Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
            viewer.wheelEvent(event)
            assert viewer.document().defaultFont().pointSizeF() == expected
        viewer.deleteLater()
    panel.deleteLater()


def test_markdown_zoom_restores_from_config_and_preview_has_no_frame(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt, QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QFrame, QMenu
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    values = {'filesystem.preview.markdown.font_size': 18}
    window = MagicMock()
    window.core.config.get.side_effect = values.get
    window.core.config.set.side_effect = values.__setitem__
    panel = PreviewPanel(window, str(tmp_path))
    path = tmp_path / 'zoom.md'
    path.write_text('# Title')
    panel.open_file(str(path))
    assert panel.viewer.frameShape() == QFrame.NoFrame
    assert panel.viewer.document().defaultFont().pointSizeF() == 18
    event = QWheelEvent(QPointF(), QPointF(), QPoint(), QPoint(0, 120),
                        Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
    panel.viewer.wheelEvent(event)
    assert values['filesystem.preview.markdown.font_size'] == 19
    window.core.config.save.assert_called_once()
    panel.show_empty()
    panel.open_file(str(path))
    assert panel.viewer.document().defaultFont().pointSizeF() == 19
    menu = QMenu()
    panel.add_file_actions(menu)
    assert not menu.actions()[0].icon().isNull()
    panel.deleteLater()


def test_back_to_preview_preserves_zoom(qapp, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt, QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    values = {'font_size': 12, 'filesystem.preview.markdown.font_size': 22}
    window = MagicMock()
    window.core.config.data = values
    window.core.config.get.side_effect = values.get
    window.core.config.set.side_effect = values.__setitem__
    panel = PreviewPanel(window, str(tmp_path))
    panel.resize(600, 400)
    path = tmp_path / 'zoom.md'
    path.write_text('# Title\n\nBody')
    panel.open_file(str(path))
    event = QWheelEvent(QPointF(), QPointF(), QPoint(), QPoint(0, 120),
                        Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
    panel.viewer.wheelEvent(event)
    assert values['filesystem.preview.markdown.font_size'] == 23
    panel.edit_markdown_source()
    panel.back_to_markdown_preview()
    assert not panel.viewer.isHidden()
    assert panel.viewer.font().pointSizeF() == 23
    assert panel.viewer.document().defaultFont().pointSizeF() == 23
    panel.deleteLater()


def test_markdown_menu_select_all_and_copy_rendered_text(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMenu
    monkeypatch.setattr('pygpt_net.tools.files.ui.preview.trans', lambda key: key)
    panel = PreviewPanel(SimpleNamespace(), str(tmp_path))
    path = tmp_path / 'copy.md'
    path.write_text('# Heading\n\n**Body**')
    panel.open_file(str(path))
    menu = QMenu()
    panel.add_file_actions(menu)
    actions = {action.text(): action for action in menu.actions()}
    assert not actions['action.copy'].isEnabled()
    actions['action.select_all'].trigger()
    menu = QMenu()
    panel.add_file_actions(menu)
    actions = {action.text(): action for action in menu.actions()}
    assert actions['action.copy'].isEnabled()
    actions['action.copy'].trigger()
    assert QApplication.clipboard().text() == panel.viewer.toPlainText()
    assert '**' not in QApplication.clipboard().text()
    panel.deleteLater()
