from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QItemSelectionModel

from pygpt_net.ui.widget.lists.base import BaseList


def test_click_selects_mode_and_backs_up_selection():
    selection = object()
    selection_model = MagicMock()
    selection_model.selection.return_value = selection
    widget = SimpleNamespace(
        id="chat",
        window=MagicMock(),
        selectionModel=lambda: selection_model,
        selection=None,
    )

    BaseList.click(widget, MagicMock())

    widget.window.controller.mode.select.assert_called_once_with("chat")
    assert widget.selection is selection


def test_lock_and_restore_selection_reselect_previous_selection():
    selection = object()
    selection_model = MagicMock()
    widget = SimpleNamespace(selection=selection, selectionModel=lambda: selection_model)

    BaseList.lockSelection(widget)
    BaseList.restore_selection(widget)

    assert selection_model.select.call_count == 2
    selection_model.select.assert_called_with(selection, QItemSelectionModel.Select)


def test_backup_selection_stores_current_selection():
    selection_model = MagicMock()
    selection_model.selection.return_value = "saved"
    widget = SimpleNamespace(selection=None, selectionModel=lambda: selection_model)

    BaseList.backup_selection(widget)
    assert widget.selection == "saved"


def test_mouse_press_ignores_invalid_index_without_calling_super():
    index = MagicMock()
    index.isValid.return_value = False
    event = MagicMock()
    widget = SimpleNamespace(indexAt=MagicMock(return_value=index))

    assert BaseList.mousePressEvent(widget, event) is None
    widget.indexAt.assert_called_once_with(event.pos())


def test_selection_command_returns_no_update_when_locked():
    widget = SimpleNamespace(unlocked=False, selection_locked=lambda: True)
    assert BaseList.selectionCommand(widget, MagicMock()) == QItemSelectionModel.NoUpdate


def test_select_by_idx_ignores_negative_and_out_of_range():
    model = MagicMock()
    model.rowCount.return_value = 2
    widget = SimpleNamespace(model=lambda: model)

    BaseList.select_by_idx(widget, -1)
    BaseList.select_by_idx(widget, 2)

    model.index.assert_not_called()


def test_select_by_idx_temporarily_unlocks_and_restores_state():
    index = object()
    model = MagicMock()
    model.rowCount.return_value = 3
    model.index.return_value = index
    selection_model = MagicMock()
    widget = SimpleNamespace(
        unlocked=False,
        model=lambda: model,
        selectionModel=lambda: selection_model,
        setCurrentIndex=MagicMock(),
        setFocus=MagicMock(),
        scrollTo=MagicMock(),
    )

    BaseList.select_by_idx(widget, 1)

    selection_model.select.assert_called_once_with(
        index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
    )
    widget.setCurrentIndex.assert_called_once_with(index)
    widget.scrollTo.assert_called_once_with(index)
    assert widget.unlocked is False


def test_scroll_position_store_restore_and_pending_values():
    vbar = MagicMock()
    hbar = MagicMock()
    vbar.value.return_value = 10
    hbar.value.return_value = 20
    widget = SimpleNamespace(
        v_scroll_value=0,
        h_scroll_value=0,
        _pending_v_scroll_value=None,
        _pending_h_scroll_value=None,
        verticalScrollBar=lambda: vbar,
        horizontalScrollBar=lambda: hbar,
    )

    BaseList.store_scroll_position(widget)
    assert (widget.v_scroll_value, widget.h_scroll_value) == (10, 20)
    BaseList.restore_scroll_position(widget)
    vbar.setValue.assert_called_with(10)
    hbar.setValue.assert_called_with(20)

    BaseList.set_pending_v_scroll(widget, "30")
    BaseList.set_pending_h_scroll(widget, 40.9)
    BaseList.apply_pending_scroll(widget)
    vbar.setValue.assert_called_with(30)
    hbar.setValue.assert_called_with(40)

    BaseList.clear_pending_scroll(widget)
    assert widget._pending_v_scroll_value is None
    assert widget._pending_h_scroll_value is None
