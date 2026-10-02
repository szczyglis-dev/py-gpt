from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
import pygpt_net.icons_rc

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.ui.widget.textarea.attachments import InputAttachments, AttachmentTile


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_strip_restores_images_scrolls_and_hides_after_send(app, tmp_path):
    path = tmp_path / 'image.png'
    image = QImage(200, 100, QImage.Format_RGB32)
    image.fill(QColor('red'))
    image.save(str(path))
    items = {'image': AttachmentItem(path=str(path), name='image.png')}
    items.update({str(n): AttachmentItem(path=f'/file{n}.pdf', name=f'file{n}.pdf') for n in range(6)})
    delete = MagicMock()
    preview = MagicMock()
    open_file = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(config=SimpleNamespace(get=lambda *args: 'dark'),
                             attachments=SimpleNamespace(get_all=lambda mode: items)),
        tools=SimpleNamespace(get=lambda name: SimpleNamespace(open_preview=preview)),
        controller=SimpleNamespace(files=SimpleNamespace(open=open_file), attachment=SimpleNamespace(delete=delete),
                                   theme=SimpleNamespace(common=SimpleNamespace(is_light_theme_id=lambda theme: False))),
    )
    parent = QWidget()
    parent.resize(300, 120)
    strip = InputAttachments(window, parent)
    strip.resize(280, strip.ROW_HEIGHT)
    heights = []
    strip.heightChanged.connect(heights.append)
    strip.sync(items, 'chat')
    parent.show()
    app.processEvents()
    assert strip.row.count() == 7
    assert not strip.row.itemAt(0).widget().image.isNull()
    assert strip.horizontalScrollBar().maximum() > 0
    assert not strip.grab().isNull()
    image_tile = strip.row.itemAt(0).widget()
    QTest.mouseClick(image_tile, Qt.LeftButton, pos=QPoint(30, 30))
    preview.assert_called_once_with(str(path))
    file_tile = strip.row.itemAt(1).widget()
    QTest.mouseClick(file_tile, Qt.LeftButton, pos=QPoint(30, 30))
    open_file.assert_called_once_with(path='/file0.pdf')
    assert image_tile.cursor().shape() == Qt.PointingHandCursor
    # Resolve index after the list changes, rather than using its original position.
    del items['image']
    strip.row.itemAt(1).widget().close.click()
    delete.assert_called_once_with(0, force=True, remove_local=False)
    assert preview.call_count == 1 and open_file.call_count == 1
    strip.mark_sent()
    assert strip.isHidden()
    assert heights[-1] == 0
    items['new'] = AttachmentItem(path='/new.txt', name='new.txt')
    strip.sync(items, 'chat')
    assert strip.row.count() == 1
    assert heights[-1] == strip.ROW_HEIGHT
    # A fresh widget after restart projects the persisted store again.
    restored = InputAttachments(window, parent)
    restored.sync(items, 'chat')
    assert restored.row.count() == len(items)
    parent.close()


def test_attachment_band_restores_previous_splitter_height():
    from pygpt_net.ui.widget.textarea.input import ChatInput
    sizes = [600, 200]
    minimum = [80]
    splitter = SimpleNamespace(sizes=lambda: list(sizes), setSizes=lambda value: sizes.__setitem__(slice(None), value),
                               isCollapsible=lambda index: True, setCollapsible=MagicMock())
    widget = SimpleNamespace(
        _attachment_row_height=0, _attachment_splitter_sizes=None,
        isVisible=lambda: True, height=lambda: 150, minimumHeight=lambda: minimum[0],
        setMinimumHeight=lambda height: minimum.__setitem__(0, height),
        _get_main_splitter=lambda: splitter,
        _find_container_in_splitter=lambda splitter: (object(), 1),
        _apply_margins=MagicMock(), _position_attachment_strip=MagicMock(),
    )
    ChatInput._attachment_height_changed(widget, 96)
    assert sizes == [504, 296]
    assert minimum[0] == 176
    splitter.setCollapsible.assert_called_with(1, False)
    assert widget._attachment_base_input_height == 150
    ChatInput._attachment_height_changed(widget, 96)
    assert sizes == [504, 296]
    assert minimum[0] == 176
    splitter.setCollapsible.assert_called_with(1, False)
    ChatInput._attachment_height_changed(widget, 0)
    assert sizes == [600, 200]
    assert minimum[0] == 80
    assert widget._attachment_splitter_sizes is None


def test_attachment_minimum_reaches_outer_composer(app):
    from pygpt_net.ui.layout.chat.input import Input
    # Outer compositor manually positions its child, so it needs an explicit minimum.
    class Composer(QWidget):
        def minimumSizeHint(self):
            return QSize(0, 165)
    tabs, composer, root = QWidget(), Composer(), Composer()
    tabs.setMinimumHeight(135)
    ui = SimpleNamespace(tabs={'input': tabs}, nodes={'input.container': composer, 'input.root': root})
    layout = SimpleNamespace(window=SimpleNamespace(ui=ui))
    Input.set_attachment_min_height(layout, 96)
    assert tabs.minimumHeight() == 231
    assert composer.minimumHeight() == root.minimumHeight() == 261
    Input.set_attachment_min_height(layout, 96)
    assert root.minimumHeight() == 261
    Input.set_attachment_min_height(layout, 0)
    assert tabs.minimumHeight() == 135
    assert composer.minimumHeight() == root.minimumHeight() == 0


def test_drag_past_attachment_minimum_then_remove_keeps_input_visible(app):
    from PySide6.QtWidgets import QSplitter, QVBoxLayout
    from pygpt_net.ui.widget.textarea.input import ChatInput
    from pygpt_net.ui.layout.chat.input import Input
    splitter = QSplitter(Qt.Vertical)
    splitter.resize(500, 800)
    output, root, editor = QWidget(), QWidget(), QWidget()
    editor.setMinimumHeight(105)
    layout = QVBoxLayout(root)
    layout.addWidget(editor)
    splitter.addWidget(output)
    splitter.addWidget(root)
    splitter.setSizes([600, 200])
    splitter.show()
    app.processEvents()
    original = splitter.sizes()
    ui = SimpleNamespace(tabs={}, nodes={'input.root': root})
    input_layout = SimpleNamespace(window=SimpleNamespace(ui=ui))
    ui.chat = SimpleNamespace(input=SimpleNamespace(
        set_attachment_min_height=lambda height: Input.set_attachment_min_height(input_layout, height)))
    widget = SimpleNamespace(
        window=SimpleNamespace(ui=ui), _attachment_row_height=0, _attachment_splitter_sizes=None,
        isVisible=editor.isVisible, height=editor.height, minimumHeight=editor.minimumHeight, setMinimumHeight=editor.setMinimumHeight,
        _get_main_splitter=lambda: splitter, _find_container_in_splitter=lambda splitter: (root, 1),
        _apply_margins=lambda: None, _position_attachment_strip=lambda: None,
    )
    ChatInput._attachment_height_changed(widget, 96)
    app.processEvents()
    splitter.moveSplitter(799, 1)
    app.processEvents()
    assert splitter.sizes()[1] > 0
    assert not splitter.isCollapsible(1)
    ChatInput._attachment_height_changed(widget, 0)
    app.processEvents()
    assert splitter.sizes()[1] >= root.minimumSizeHint().height()
    assert abs(splitter.sizes()[1] - original[1]) <= 2
    assert splitter.isCollapsible(1)
    splitter.close()


def test_startup_ignores_provisional_editor_height():
    from pygpt_net.ui.widget.textarea.input import ChatInput
    sizes = [400, 300]
    minimum = [105]
    splitter = SimpleNamespace(sizes=lambda: list(sizes), setSizes=MagicMock(),
                               isCollapsible=lambda index: True, setCollapsible=MagicMock())
    widget = SimpleNamespace(
        _attachment_row_height=0, _attachment_splitter_sizes=None,
        isVisible=lambda: False, height=lambda: 480, minimumHeight=lambda: minimum[0],
        setMinimumHeight=lambda height: minimum.__setitem__(0, height),
        _get_main_splitter=lambda: splitter, _find_container_in_splitter=lambda splitter: (object(), 1),
        _apply_margins=lambda: None, _position_attachment_strip=lambda: None,
    )
    ChatInput._attachment_height_changed(widget, 96)
    assert widget._attachment_base_input_height == 105
    assert minimum[0] == 201
    assert widget._attachment_splitter_sizes is None
    splitter.setSizes.assert_not_called()
    ChatInput._attachment_height_changed(widget, 0)
    assert minimum[0] == 105
    splitter.setSizes.assert_not_called()
