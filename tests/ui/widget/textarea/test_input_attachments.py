from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget
import pygpt_net.icons_rc

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.ui.widget.textarea.attachments import InputAttachments


@pytest.fixture
def app(qapp):
    return qapp


@pytest.fixture(autouse=True)
def synchronous_layout_callbacks(monkeypatch):
    # Run layout callbacks explicitly, never leave them in the global Qt queue.
    monkeypatch.setattr('PySide6.QtCore.QTimer.singleShot', lambda delay, callback: callback())


def test_reorder_updates_attachment_store_and_saves_without_moving_sent_items():
    items = {key: AttachmentItem(path=f'/{key}.txt') for key in ('a', 'sent', 'b', 'c')}
    save, refresh = MagicMock(), MagicMock()
    strip = SimpleNamespace(mode='chat', sent={'sent'}, window=SimpleNamespace(
        core=SimpleNamespace(attachments=SimpleNamespace(get_all=lambda mode: items, save=save)),
        controller=SimpleNamespace(attachment=SimpleNamespace(update=refresh))))
    InputAttachments.move_attachment(strip, 'c', 0)
    assert list(items) == ['c', 'sent', 'a', 'b']
    save.assert_called_once()
    refresh.assert_called_once()
    InputAttachments.move_attachment(strip, 'c', 3)
    assert list(items) == ['a', 'sent', 'b', 'c']
    InputAttachments.move_attachment(strip, 'sent', 0)
    InputAttachments.move_attachment(strip, 'c', 3)
    assert save.call_count == refresh.call_count == 2


def test_drop_insertion_position_accounts_for_source_removal():
    items = {key: AttachmentItem(path=f'/{key}.txt') for key in ('a', 'b', 'c')}
    strip = SimpleNamespace(mode='chat', sent=set(), window=SimpleNamespace(
        core=SimpleNamespace(attachments=SimpleNamespace(get_all=lambda mode: items, save=MagicMock())),
        controller=SimpleNamespace(attachment=SimpleNamespace(update=MagicMock()))))
    InputAttachments.move_attachment(strip, 'a', 2)
    assert list(items) == ['b', 'a', 'c']


def test_strip_restores_images_routes_actions_and_hides_after_send(app, tmp_path):
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
        tools=SimpleNamespace(get=lambda name: SimpleNamespace(open_preview=preview, paths=SimpleNamespace(open=open_file))),
        ui=SimpleNamespace(nodes={'input': SimpleNamespace(fit_to_content=MagicMock())}),
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
    assert strip.row.count() == 7
    assert not strip.row.itemAt(0).widget().image.isNull()
    image_tile = strip.row.itemAt(0).widget()
    image_tile.open_attachment(True)
    preview.assert_called_once_with(str(path))
    file_tile = strip.row.itemAt(1).widget()
    file_tile.open_attachment(False)
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


def test_attachment_band_updates_minimum_and_releases_collapse_guard():
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
        fit_to_content=MagicMock(),
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
    assert sizes == [504, 296]
    widget.fit_to_content.assert_called_once_with()
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


def test_attachment_band_preserves_user_resize_when_removed():
    from pygpt_net.ui.widget.textarea.input import ChatInput
    sizes = [600, 200]
    minimum = [105]
    splitter = SimpleNamespace(
        sizes=lambda: list(sizes),
        setSizes=lambda value: sizes.__setitem__(slice(None), value),
        isCollapsible=lambda index: True, setCollapsible=MagicMock(),
    )
    widget = SimpleNamespace(
        _attachment_row_height=0, _attachment_splitter_sizes=None,
        isVisible=lambda: True, height=lambda: 150, minimumHeight=lambda: minimum[0],
        setMinimumHeight=lambda value: minimum.__setitem__(0, value),
        _get_main_splitter=lambda: splitter,
        _find_container_in_splitter=lambda value: (object(), 1),
        _apply_margins=MagicMock(), _position_attachment_strip=MagicMock(),
        fit_to_content=MagicMock(),
    )
    ChatInput._attachment_height_changed(widget, 96)
    splitter.setCollapsible.assert_called_with(1, False)
    sizes[:] = [500, 300]
    ChatInput._attachment_height_changed(widget, 0)
    assert sizes == [500, 300]
    widget.fit_to_content.assert_called_once_with()
    assert minimum[0] == 105
    splitter.setCollapsible.assert_called_with(1, True)


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
        fit_to_content=MagicMock(),
    )
    ChatInput._attachment_height_changed(widget, 96)
    assert widget._attachment_base_input_height == 105
    assert minimum[0] == 201
    assert widget._attachment_splitter_sizes is None
    splitter.setSizes.assert_not_called()
    ChatInput._attachment_height_changed(widget, 0)
    assert minimum[0] == 105
    splitter.setSizes.assert_not_called()


def test_attachment_minimum_is_recomputed_when_visible_hint_changes(app):
    from pygpt_net.ui.layout.chat.input import Input
    class Composer(QWidget):
        def minimumSizeHint(self):
            return QSize(100, self.hint_height)
        def isVisible(self):
            return self.hint_height > 0
        hint_height = 0
    composer = Composer()
    ui = SimpleNamespace(tabs={}, nodes={'input.root': composer})
    layout = SimpleNamespace(window=SimpleNamespace(ui=ui))
    Input.set_attachment_min_height(layout, 96)
    assert composer.minimumHeight() == 96
    composer.hint_height = 261
    Input.set_attachment_min_height(layout, 96)
    assert composer.minimumHeight() == 261
    Input.set_attachment_min_height(layout, 96)
    assert composer.minimumHeight() == 261
    Input.set_attachment_min_height(layout, 0)
    assert composer.minimumHeight() == 0
    composer.close()


def test_parent_minimum_counts_attachment_band_once_across_tab_returns(app):
    from PySide6.QtWidgets import QVBoxLayout
    from pygpt_net.ui.widget.textarea.input import ChatInput
    from pygpt_net.ui.layout.chat.input import Input
    root, editor = QWidget(), QWidget()
    editor.setMinimumHeight(105)
    parent_layout = QVBoxLayout(root)
    parent_layout.addWidget(editor)
    baseline = root.minimumSizeHint().height()
    ui = SimpleNamespace(tabs={}, nodes={'input.root': root})
    layout = SimpleNamespace(window=SimpleNamespace(ui=ui))
    ui.chat = SimpleNamespace(input=SimpleNamespace(
        set_attachment_min_height=lambda height: Input.set_attachment_min_height(layout, height)))
    widget = SimpleNamespace(window=SimpleNamespace(ui=ui),
        _attachment_row_height=0, _attachment_splitter_sizes=None,
        isVisible=editor.isVisible, height=editor.height, minimumHeight=editor.minimumHeight,
        setMinimumHeight=editor.setMinimumHeight, _get_main_splitter=lambda: None,
        _find_container_in_splitter=lambda splitter: (None, -1),
        _apply_margins=lambda: None, _position_attachment_strip=lambda: None,
        fit_to_content=MagicMock())
    ChatInput._attachment_height_changed(widget, 104)
    assert root.minimumHeight() == baseline + 104
    for _ in range(3):
        parent_layout.invalidate()
        parent_layout.activate()
        Input.set_attachment_min_height(layout, 104)
        assert root.minimumHeight() == baseline + 104
    ChatInput._attachment_height_changed(widget, 0)
    assert root.minimumHeight() == 0
    assert editor.minimumHeight() == 105
    root.close()


def test_connection_tiles_follow_files_show_reader_name_and_default_icon(app):
    window = MagicMock()
    window.core.config.get.return_value = 'dark'
    window.controller.theme.common.is_light_theme_id.return_value = False
    items = {'web': AttachmentItem(name='source-id', path='source-id', type=AttachmentItem.TYPE_URL,
                                  extra={'loader': 'database', 'loader_name': 'Database'}),
             'file': AttachmentItem(name='note.txt', path='/note.txt')}
    parent = QWidget()
    strip = InputAttachments(window, parent)
    try:
        strip.sync(items, 'chat')
        assert strip.row.itemAt(0).widget().name == 'note.txt'
        tile = strip.row.itemAt(1).widget()
        assert tile.name == 'Database'
        assert tile.is_connection and tile.image.isNull()
        assert not tile.icon.pixmap(16, 16).isNull()
    finally:
        parent.close()


def test_web_reader_attachment_reappears_above_input_when_edited_after_send(app):
    window = MagicMock()
    window.core.config.get.return_value = 'dark'
    window.controller.theme.common.is_light_theme_id.return_value = False
    source = AttachmentItem(id='youtube', name='video-url', path='video-url', type=AttachmentItem.TYPE_URL,
                            extra={'loader': 'youtube', 'loader_name': 'YouTube', 'loader_icon': ':/icons/language.svg'})
    items = {'youtube': source}
    window.core.attachments.get_all.return_value = items
    parent = QWidget()
    strip = InputAttachments(window, parent)
    heights = []
    strip.heightChanged.connect(heights.append)
    try:
        strip.sync(items, 'chat')
        strip.mark_sent()
        assert strip.isHidden()
        strip.show_pending('youtube')
        assert not strip.isHidden()
        tile = strip.row.itemAt(0).widget()
        assert tile.name == 'YouTube' and tile.is_connection
        from PySide6.QtGui import QIcon
        assert tile.icon.pixmap(16, 16).toImage() == QIcon(':/icons/language.svg').pixmap(16, 16).toImage()
        assert heights[-1] == strip.ROW_HEIGHT
    finally:
        parent.close()


def test_reader_dialog_submission_creates_visible_attachment_tile(app):
    from pygpt_net.core.attachments.attachments import Attachments
    from pygpt_net.controller.attachment.attachment import Attachment as Controller
    window = MagicMock()
    window.core.config.get.side_effect = lambda key, *args: 'chat' if key == 'mode' else False
    window.controller.theme.common.is_light_theme_id.return_value = False
    store = Attachments(window)
    store.save = MagicMock()
    window.core.attachments = store
    provider = SimpleNamespace(name='YouTube', icon=':/icons/language.svg', get_external_id=lambda params: params['url'])
    window.core.idx.indexing.get_loader.return_value = provider
    window.core.idx.ui.loaders.handle_options.return_value = (True, 'youtube', {'url': 'https://youtu.be/F3uvhqiKrcI'}, {})
    parent = QWidget()
    strip = InputAttachments(window, parent)
    window.ui.nodes = {'input': SimpleNamespace(attachment_strip=strip), 'dialog.url.loader': MagicMock()}
    window.ui.dialog = {'url': SimpleNamespace(current='', close=MagicMock())}
    ctrl = Controller(window)
    ctrl.update_tab = MagicMock()
    try:
        ctrl.attach_url()
        assert strip.row.count() == 1 and not strip.isHidden()
        tile = strip.row.itemAt(0).widget()
        assert tile.name == 'YouTube' and tile.is_connection
        assert not tile.icon.pixmap(16, 16).isNull()
        window.core.idx.indexing.read_web_content.assert_not_called()
    finally:
        parent.close()
