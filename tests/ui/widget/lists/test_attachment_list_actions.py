from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.lists.attachment import AttachmentList


def _widget(row=2):
    index = MagicMock(); index.row.return_value = row
    attachment = SimpleNamespace(
        open=MagicMock(), open_dir=MagicMock(), rename=MagicMock(), delete=MagicMock(),
        from_clipboard_image=MagicMock(), from_clipboard_url=MagicMock(), from_clipboard_text=MagicMock(),
    )
    window = SimpleNamespace(
        controller=SimpleNamespace(attachment=attachment),
        core=SimpleNamespace(config=SimpleNamespace(get=MagicMock(return_value="chat"))),
    )
    return SimpleNamespace(window=window, indexAt=MagicMock(return_value=index), _backup_selection=None, restore_after_ctx_menu=True)


def test_attachment_column_widths_follow_configured_proportion():
    hdr = MagicMock()
    hdr.count.return_value = 4
    widget = SimpleNamespace(
        header=lambda: hdr,
        viewport=lambda: SimpleNamespace(width=lambda: 1000),
        width=lambda: 800,
        column_proportion=0.4,
        columnWidth=lambda column: 0,
        setColumnWidth=MagicMock(),
    )
    AttachmentList.adjustColumnWidths(widget)
    assert widget.setColumnWidth.call_args_list[0].args == (0, 400)
    assert [call.args for call in widget.setColumnWidth.call_args_list[1:]] == [(1, 200), (2, 200), (3, 200)]


def test_attachment_selection_helpers_sort_rows_and_handle_errors():
    sm = MagicMock()
    a, b = MagicMock(), MagicMock(); a.row.return_value = 4; b.row.return_value = 1
    sm.selectedRows.return_value = [a, b]
    widget = SimpleNamespace(selectionModel=lambda: sm)
    assert AttachmentList._selected_rows(widget) == [4, 1]
    assert AttachmentList._has_multi_selection(widget) is True

    bad = SimpleNamespace(selectionModel=MagicMock(side_effect=RuntimeError()))
    assert AttachmentList._selected_rows(bad) == []
    assert AttachmentList._has_multi_selection(bad) is False


def test_attachment_keypress_pastes_only_on_ctrl_v():
    widget = SimpleNamespace(handle_paste=MagicMock())
    event = MagicMock(); event.key.return_value = Qt.Key_V; event.modifiers.return_value = Qt.ControlModifier
    AttachmentList.keyPressEvent(widget, event)
    widget.handle_paste.assert_called_once_with()

    widget.handle_paste.reset_mock(); event.key.return_value = Qt.Key_A
    AttachmentList.keyPressEvent(widget, event)
    widget.handle_paste.assert_not_called()


def test_attachment_single_actions_dispatch_mode_and_row():
    widget = _widget(3)
    event = MagicMock()
    for method, target in [
        (AttachmentList.action_open, "open"),
        (AttachmentList.action_open_dir, "open_dir"),
        (AttachmentList.action_rename, "rename"),
    ]:
        method(widget, event)
        getattr(widget.window.controller.attachment, target).assert_called_once_with("chat", 3)
    AttachmentList.action_delete(widget, event)
    widget.window.controller.attachment.delete.assert_called_once_with(3)


def test_attachment_index_and_multi_actions_aggregate_rows():
    widget = _widget()
    AttachmentList._action_open_idx(widget, 2)
    AttachmentList._action_open_dir_idx(widget, 3)
    AttachmentList._action_rename_idx(widget, 4)
    AttachmentList._action_delete_idx(widget, 5)
    AttachmentList._action_open_multi(widget, [1, 4])
    AttachmentList._action_open_dir_multi(widget, [2, 7])
    AttachmentList._action_delete_multi(widget, [3, 8])

    a = widget.window.controller.attachment
    a.open.assert_any_call("chat", 2)
    a.open.assert_any_call("chat", [1, 4])
    a.open_dir.assert_any_call("chat", 3)
    a.open_dir.assert_any_call("chat", [2, 7])
    a.rename.assert_called_once_with("chat", 4)
    a.delete.assert_any_call(5)
    a.delete.assert_any_call([3, 8])


def test_attachment_paste_prefers_image_then_urls_then_text():
    widget = _widget()
    source = MagicMock()
    clipboard = MagicMock(); clipboard.mimeData.return_value = source

    image = MagicMock()
    source.hasImage.return_value = True
    source.imageData.return_value = image
    with patch("pygpt_net.ui.widget.lists.attachment.QApplication.clipboard", return_value=clipboard), \
         patch("pygpt_net.ui.widget.lists.attachment.QImage", type(image)):
        AttachmentList.handle_paste(widget)
    widget.window.controller.attachment.from_clipboard_image.assert_called_once_with(image)

    widget.window.controller.attachment.from_clipboard_image.reset_mock()
    source.hasImage.return_value = False; source.hasUrls.return_value = True
    local = MagicMock(); local.isLocalFile.return_value = True; local.toLocalFile.return_value = "/tmp/a.txt"
    remote = MagicMock(); remote.isLocalFile.return_value = False
    source.urls.return_value = [local, remote]
    with patch("pygpt_net.ui.widget.lists.attachment.QApplication.clipboard", return_value=clipboard):
        AttachmentList.handle_paste(widget)
    widget.window.controller.attachment.from_clipboard_url.assert_called_once_with("/tmp/a.txt", all=True)

    source.hasUrls.return_value = False; source.hasText.return_value = True; source.text.return_value = "abc"
    with patch("pygpt_net.ui.widget.lists.attachment.QApplication.clipboard", return_value=clipboard):
        AttachmentList.handle_paste(widget)
    widget.window.controller.attachment.from_clipboard_text.assert_called_once_with("abc", all=True)
