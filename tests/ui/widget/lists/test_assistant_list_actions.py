from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.lists.assistant import AssistantList


def _idx(row):
    index = MagicMock()
    index.row.return_value = row
    return index


def test_assistant_selection_helpers_are_exception_safe():
    selection = MagicMock()
    selection.selectedRows.return_value = [_idx(3), _idx(1)]
    widget = SimpleNamespace(selectionModel=lambda: selection)

    assert [x.row() for x in AssistantList._selected_indexes(widget)] == [3, 1]
    assert AssistantList._selected_rows(widget) == [3, 1]
    assert AssistantList._has_multi_selection(widget) is True

    bad = SimpleNamespace(selectionModel=MagicMock(side_effect=RuntimeError("x")))
    assert AssistantList._selected_indexes(bad) == []
    assert AssistantList._selected_rows(bad) == []
    assert AssistantList._has_multi_selection(bad) is False


def test_assistant_click_suppression_and_multi_selection_do_not_dispatch():
    controller = SimpleNamespace(assistant=SimpleNamespace(select=MagicMock()))
    widget = SimpleNamespace(
        window=SimpleNamespace(controller=controller),
        _suppress_item_click=True,
        _has_multi_selection=MagicMock(return_value=False),
    )
    AssistantList.click(widget, _idx(2))
    assert widget._suppress_item_click is False
    controller.assistant.select.assert_not_called()

    widget._has_multi_selection.return_value = True
    AssistantList.click(widget, _idx(2))
    controller.assistant.select.assert_not_called()


def test_assistant_click_and_double_click_dispatch_valid_rows():
    assistant = SimpleNamespace(select=MagicMock(), editor=SimpleNamespace(edit=MagicMock()))
    widget = SimpleNamespace(
        window=SimpleNamespace(controller=SimpleNamespace(assistant=assistant)),
        _suppress_item_click=False,
        _has_multi_selection=MagicMock(return_value=False),
    )
    AssistantList.click(widget, _idx(4))
    AssistantList.dblclick(widget, _idx(5))
    AssistantList.dblclick(widget, _idx(-1))
    assistant.select.assert_called_once_with(4)
    assistant.editor.edit.assert_called_once_with(5)


def test_assistant_edit_and_delete_support_single_and_multi_rows():
    assistant = SimpleNamespace(delete=MagicMock(), editor=SimpleNamespace(edit=MagicMock()))
    widget = SimpleNamespace(
        window=SimpleNamespace(controller=SimpleNamespace(assistant=assistant)),
        restore_after_ctx_menu=True,
    )

    AssistantList.action_edit(widget, _idx(2))
    assistant.editor.edit.assert_called_once_with(2)
    assert widget.restore_after_ctx_menu is False

    widget.restore_after_ctx_menu = True
    AssistantList.action_delete(widget, [4, 1])
    assistant.delete.assert_called_with([4, 1])
    assert widget.restore_after_ctx_menu is False

    widget.restore_after_ctx_menu = True
    AssistantList.action_delete(widget, _idx(3))
    assistant.delete.assert_called_with(3)
    assert widget.restore_after_ctx_menu is False
