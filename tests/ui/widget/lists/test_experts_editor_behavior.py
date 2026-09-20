from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6 import QtCore

from pygpt_net.ui.widget.lists.experts import ExpertsList, ExpertsEditor


def test_experts_selected_rows_and_actions():
    sm = MagicMock(); sm.selectedRows.return_value = ["a", "b"]
    widget = SimpleNamespace(
        selectionModel=lambda: sm,
        restore_after_ctx_menu=True,
        window=SimpleNamespace(controller=SimpleNamespace(presets=SimpleNamespace(
            editor=SimpleNamespace(experts=SimpleNamespace(add_expert=MagicMock(), remove_expert=MagicMock()))
        ))),
    )
    assert ExpertsList._selected_rows(widget) == ["a", "b"]
    ExpertsList._action_add(widget)
    assert widget.restore_after_ctx_menu is False
    widget.window.controller.presets.editor.experts.add_expert.assert_called_once_with()
    widget.restore_after_ctx_menu = True
    ExpertsList._action_remove(widget)
    widget.window.controller.presets.editor.experts.remove_expert.assert_called_once_with()


def _model():
    model = MagicMock()
    model.rowCount.return_value = 2
    model.index.side_effect = lambda r, c: (r, c)
    return model


def _entry(name, filename, uuid):
    return SimpleNamespace(name=name, filename=filename, uuid=uuid)


def test_experts_editor_update_available_populates_names_tooltips_and_restores_selection():
    model = _model(); node = MagicMock()
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(
        models={"preset.experts.available": model},
        nodes={"preset.experts.available": node},
    )))
    data = {"a": _entry("Alpha", "a.json", "u1"), "b": _entry("Beta", "b.json", "u2")}

    ExpertsEditor.update_available(widget, data)

    node.backup_selection.assert_called_once_with()
    model.removeRows.assert_called_once_with(0, 2)
    assert model.insertRow.call_count == 2
    model.setData.assert_any_call((0, 0), "u1", QtCore.Qt.ToolTipRole)
    model.setData.assert_any_call((0, 0), "Alpha  [a.json]")
    model.setData.assert_any_call((1, 0), "Beta  [b.json]")
    node.restore_selection.assert_called_once_with()


def test_experts_editor_update_selected_and_update_lists_delegate_both_sides():
    model = _model(); node = MagicMock()
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(
        models={"preset.experts.selected": model},
        nodes={"preset.experts.selected": node},
    )))
    data = {"a": _entry("Alpha", "a.json", "u1")}
    ExpertsEditor.update_selected(widget, data)
    model.setData.assert_any_call((0, 0), "u1", QtCore.Qt.ToolTipRole)
    node.restore_selection.assert_called_once_with()

    combined = SimpleNamespace(update_available=MagicMock(), update_selected=MagicMock())
    ExpertsEditor.update_lists(combined, {"x": 1}, {"y": 2})
    combined.update_available.assert_called_once_with({"x": 1})
    combined.update_selected.assert_called_once_with({"y": 2})
