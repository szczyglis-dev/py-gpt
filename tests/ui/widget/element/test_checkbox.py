from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.element.checkbox import ColorCheckbox


def _widget(selected=None, boxes=None):
    controller = MagicMock()
    return SimpleNamespace(
        selected=list(selected or []),
        boxes=boxes or {},
        window=SimpleNamespace(controller=SimpleNamespace(ctx=controller)),
    )


def test_update_colors_accepts_bool_and_qt_check_state_without_duplicates():
    widget = _widget([1])

    ColorCheckbox.update_colors(widget, True, 2)
    ColorCheckbox.update_colors(widget, Qt.Checked, 2)

    assert widget.selected == [1, 2]
    assert widget.window.controller.ctx.label_filters_changed.call_count == 2
    widget.window.controller.ctx.label_filters_changed.assert_called_with([1, 2])


def test_update_colors_removes_only_existing_selection():
    widget = _widget([1, 2])

    ColorCheckbox.update_colors(widget, False, 1)
    ColorCheckbox.update_colors(widget, Qt.Unchecked, 99)

    assert widget.selected == [2]


def test_restore_checks_known_boxes_with_signals_blocked():
    one = MagicMock()
    one.blockSignals.return_value = False
    widget = _widget(boxes={1: one})

    ColorCheckbox.restore(widget, [1, 99])

    assert widget.selected == [1, 99]
    assert one.blockSignals.call_args_list[0].args == (True,)
    one.setChecked.assert_called_once_with(True)
    assert one.blockSignals.call_args_list[1].args == (False,)
    widget.window.controller.ctx.label_filters_changed.assert_called_once_with([1, 99])
