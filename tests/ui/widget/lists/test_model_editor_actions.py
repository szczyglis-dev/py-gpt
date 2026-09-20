from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.lists.model_editor import ModelEditorList


def _widget():
    editor = SimpleNamespace(
        select=MagicMock(), set_hidden_by_idx=MagicMock(), delete_by_idx=MagicMock(), duplicate_by_idx=MagicMock()
    )
    return SimpleNamespace(
        window=SimpleNamespace(controller=SimpleNamespace(model=SimpleNamespace(editor=editor))),
        restore_after_ctx_menu=True,
    )


def test_model_editor_selection_helpers_sort_and_are_exception_safe():
    sm = MagicMock(); a = MagicMock(); b = MagicMock(); a.row.return_value = 5; b.row.return_value = 1
    sm.selectedRows.return_value = [a, b]
    widget = SimpleNamespace(selectionModel=lambda: sm)
    assert ModelEditorList._selected_rows(widget) == [1, 5]
    assert ModelEditorList._has_multi_selection(widget) is True
    bad = SimpleNamespace(selectionModel=MagicMock(side_effect=RuntimeError()))
    assert ModelEditorList._selected_rows(bad) == []
    assert ModelEditorList._has_multi_selection(bad) is False


def test_model_editor_visibility_action_always_passes_target_and_hidden_state():
    widget = _widget()
    ModelEditorList.action_visibility(widget, [1, 3], hidden=True)
    widget.window.controller.model.editor.set_hidden_by_idx.assert_called_once_with([1, 3], True)
    assert widget.restore_after_ctx_menu is False


def test_model_editor_delete_supports_single_multi_and_ignores_invalid_or_empty():
    widget = _widget(); editor = widget.window.controller.model.editor
    ModelEditorList.action_delete(widget, [4, 2])
    editor.delete_by_idx.assert_called_once_with([4, 2])
    editor.delete_by_idx.reset_mock(); widget.restore_after_ctx_menu = True
    ModelEditorList.action_delete(widget, [])
    ModelEditorList.action_delete(widget, -1)
    editor.delete_by_idx.assert_not_called()
    assert widget.restore_after_ctx_menu is True
    ModelEditorList.action_delete(widget, 3)
    editor.delete_by_idx.assert_called_once_with(3)


def test_model_editor_duplicate_supports_single_multi_and_ignores_invalid_or_empty():
    widget = _widget(); editor = widget.window.controller.model.editor
    ModelEditorList.action_duplicate(widget, [1, 2])
    editor.duplicate_by_idx.assert_called_once_with([1, 2])
    editor.duplicate_by_idx.reset_mock(); widget.restore_after_ctx_menu = True
    ModelEditorList.action_duplicate(widget, [])
    ModelEditorList.action_duplicate(widget, -1)
    editor.duplicate_by_idx.assert_not_called()
    ModelEditorList.action_duplicate(widget, 7)
    editor.duplicate_by_idx.assert_called_once_with(7)
