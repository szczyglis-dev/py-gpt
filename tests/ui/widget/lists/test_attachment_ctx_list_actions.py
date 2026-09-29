from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.lists.attachment_ctx import AttachmentCtxList


def _widget(row=2):
    index = MagicMock(); index.row.return_value = row
    attachment = SimpleNamespace(
        delete_by_idx=MagicMock(), open_by_idx=MagicMock(),
        open_dir_src_by_idx=MagicMock(), open_dir_dest_by_idx=MagicMock(),
    )
    return SimpleNamespace(
        window=SimpleNamespace(controller=SimpleNamespace(chat=SimpleNamespace(attachment=attachment))),
        indexAt=MagicMock(return_value=index),
    )


def test_attachment_ctx_column_widths_use_three_equal_columns():
    widget = SimpleNamespace(
        viewport=lambda: SimpleNamespace(width=lambda: 900),
        active_column_width=58,
        column_proportion=0.4,
        setColumnWidth=MagicMock(),
    )
    AttachmentCtxList.adjustColumnWidths(widget)
    assert [c.args for c in widget.setColumnWidth.call_args_list] == [
        (0, 58), (1, 336), (2, 126), (3, 126), (4, 126), (5, 126)
    ]


def test_attachment_ctx_selection_helpers_sort_and_are_exception_safe():
    sm = MagicMock(); i1 = MagicMock(); i2 = MagicMock(); i1.row.return_value = 5; i2.row.return_value = 2
    sm.selectedRows.return_value = [i1, i2]
    widget = SimpleNamespace(selectionModel=lambda: sm)
    assert AttachmentCtxList._selected_rows(widget) == [5, 2]
    assert AttachmentCtxList._has_multi_selection(widget) is True

    bad = SimpleNamespace(selectionModel=MagicMock(side_effect=RuntimeError()))
    assert AttachmentCtxList._selected_rows(bad) == []
    assert AttachmentCtxList._has_multi_selection(bad) is False


def test_attachment_ctx_single_actions_dispatch_selected_row():
    widget = _widget(4); event = MagicMock()
    mapping = [
        (AttachmentCtxList.action_delete, "delete_by_idx"),
        (AttachmentCtxList.action_open, "open_by_idx"),
        (AttachmentCtxList.action_open_dir_src, "open_dir_src_by_idx"),
        (AttachmentCtxList.action_open_dir_dest, "open_dir_dest_by_idx"),
    ]
    for method, target in mapping:
        method(widget, event)
        getattr(widget.window.controller.chat.attachment, target).assert_called_once_with(4)


def test_attachment_ctx_multi_actions_pass_row_lists_and_ignore_empty():
    widget = _widget()
    mapping = [
        (AttachmentCtxList._action_delete_multi, "delete_by_idx"),
        (AttachmentCtxList._action_open_multi, "open_by_idx"),
        (AttachmentCtxList._action_open_dir_src_multi, "open_dir_src_by_idx"),
        (AttachmentCtxList._action_open_dir_dest_multi, "open_dir_dest_by_idx"),
    ]
    for method, target in mapping:
        method(widget, [1, 3])
        getattr(widget.window.controller.chat.attachment, target).assert_called_once_with([1, 3])
        getattr(widget.window.controller.chat.attachment, target).reset_mock()
        method(widget, [])
        getattr(widget.window.controller.chat.attachment, target).assert_not_called()
