from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.lists.uploaded import UploadedFileList


def _widget():
    files = SimpleNamespace(select=MagicMock(), rename=MagicMock(), download=MagicMock(), delete=MagicMock())
    return SimpleNamespace(
        window=SimpleNamespace(controller=SimpleNamespace(assistant=SimpleNamespace(files=files))),
        restore_after_ctx_menu=True,
    )


def test_uploaded_file_column_widths_and_selection_helpers():
    widget = SimpleNamespace(width=lambda: 1000, column_proportion=0.25, setColumnWidth=MagicMock())
    UploadedFileList.adjustColumnWidths(widget)
    assert [c.args for c in widget.setColumnWidth.call_args_list] == [(0, 250), (1, 250), (2, 250), (3, 250)]

    sm = MagicMock(); a = MagicMock(); b = MagicMock(); a.row.return_value = 7; b.row.return_value = 1
    sm.selectedRows.return_value = [a, b]
    sel_widget = SimpleNamespace(selectionModel=lambda: sm)
    assert UploadedFileList._selected_rows(sel_widget) == [1, 7]
    assert UploadedFileList._has_multi_selection(sel_widget) is True


def test_uploaded_file_double_click_selects_valid_row_only():
    widget = _widget()
    index = MagicMock(); index.row.return_value = 3
    UploadedFileList.dblclick(widget, index)
    widget.window.controller.assistant.files.select.assert_called_once_with(3)
    index.row.return_value = -1
    UploadedFileList.dblclick(widget, index)
    assert widget.window.controller.assistant.files.select.call_count == 1


@pytest.mark.parametrize("method,target", [
    (UploadedFileList.action_rename, "rename"),
    (UploadedFileList.action_download, "download"),
    (UploadedFileList.action_delete, "delete"),
])
def test_uploaded_file_actions_support_single_multi_and_ignore_invalid(method, target):
    widget = _widget(); fn = getattr(widget.window.controller.assistant.files, target)
    method(widget, [3, 1])
    fn.assert_called_once_with([3, 1])
    assert widget.restore_after_ctx_menu is False

    fn.reset_mock(); widget.restore_after_ctx_menu = True
    method(widget, [])
    method(widget, -1)
    fn.assert_not_called()
    assert widget.restore_after_ctx_menu is True

    method(widget, 6)
    fn.assert_called_once_with(6)
    assert widget.restore_after_ctx_menu is False
