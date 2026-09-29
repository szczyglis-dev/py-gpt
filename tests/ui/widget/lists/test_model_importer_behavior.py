from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6 import QtCore

from pygpt_net.ui.widget.lists.model_importer import ImporterList, ModelImporter


def test_importer_list_selection_is_exception_safe_and_actions_delegate():
    sm = MagicMock(); sm.selectedRows.return_value = [1, 2]
    importer = SimpleNamespace(add=MagicMock(), remove=MagicMock())
    widget = SimpleNamespace(
        selectionModel=lambda: sm,
        restore_after_ctx_menu=True,
        window=SimpleNamespace(controller=SimpleNamespace(model=SimpleNamespace(importer=importer))),
    )
    assert ImporterList._selected_rows(widget) == [1, 2]
    ImporterList._action_import(widget)
    assert widget.restore_after_ctx_menu is False
    importer.add.assert_called_once_with()
    widget.restore_after_ctx_menu = True
    ImporterList._action_remove(widget)
    importer.remove.assert_called_once_with()

    bad = SimpleNamespace(selectionModel=MagicMock(side_effect=RuntimeError()))
    assert ImporterList._selected_rows(bad) == []


def _model():
    model = MagicMock(); model.rowCount.return_value = 5; model.index.side_effect = lambda r, c: (r, c)
    return model


def _entry(id, name=None, imported=False):
    return SimpleNamespace(id=id, name=name if name is not None else id, imported=imported)


def test_model_importer_update_available_marks_current_models_when_all_enabled():
    model = _model(); node = MagicMock()
    importer = SimpleNamespace(all=True, in_current=MagicMock(side_effect=lambda mid: mid == "m2"))
    widget = SimpleNamespace(window=SimpleNamespace(
        ui=SimpleNamespace(models={"models.importer.available": model}, nodes={"models.importer.available": node}),
        controller=SimpleNamespace(model=SimpleNamespace(importer=importer)),
    ))
    data = {"a": _entry("m1", "Model One"), "b": _entry("m2")}

    ModelImporter.update_available(widget, data)

    node.backup_selection.assert_called_once_with()
    model.removeRows.assert_called_once_with(0, 5)
    model.setData.assert_any_call((0, 0), "m1", QtCore.Qt.ToolTipRole)
    model.setData.assert_any_call((0, 0), "m1 (Model One)")
    model.setData.assert_any_call((1, 0), "m2 *")
    node.restore_selection.assert_called_once_with()


def test_model_importer_update_current_marks_renamed_and_imported_models():
    model = _model(); node = MagicMock()
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(
        models={"models.importer.current": model}, nodes={"models.importer.current": node}
    )))
    data = {"a": _entry("m1", "Pretty", True), "b": _entry("m2", "m2", False)}

    ModelImporter.update_current(widget, data)

    model.setData.assert_any_call((0, 0), "m1", QtCore.Qt.ToolTipRole)
    model.setData.assert_any_call((0, 0), "* m1 --> Pretty")
    model.setData.assert_any_call((1, 0), "m2")
    node.restore_selection.assert_called_once_with()


def test_model_importer_update_lists_delegates_both_collections():
    widget = SimpleNamespace(update_available=MagicMock(), update_current=MagicMock())
    ModelImporter.update_lists(widget, {"a": 1}, {"b": 2})
    widget.update_available.assert_called_once_with({"a": 1})
    widget.update_current.assert_called_once_with({"b": 2})
