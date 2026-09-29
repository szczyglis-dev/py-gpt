from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.lists.index_combo import IndexCombo


def _widget(current="idx", virtual="virtual", group="g1"):
    indexer = SimpleNamespace(
        index_project=MagicMock(), index_ctx_from_ts=MagicMock(), index_ctx_current=MagicMock(),
        index_all_files=MagicMock(), truncate_project=MagicMock(), clear=MagicMock(), truncate=MagicMock(),
    )
    project = SimpleNamespace(VIRTUAL_ID=virtual, get_current_group_id=MagicMock(return_value=group))
    widget = SimpleNamespace(
        current_id=current,
        combo=MagicMock(),
        window=SimpleNamespace(
            controller=SimpleNamespace(idx=SimpleNamespace(select_by_id=MagicMock(), indexer=indexer), settings=SimpleNamespace(open_section=MagicMock())),
            core=SimpleNamespace(idx=SimpleNamespace(project=project)),
        ),
    )
    widget._current_project_group_id = lambda: IndexCombo._current_project_group_id(widget)
    return widget


def test_index_combo_change_selects_item_data():
    widget = _widget(); widget.combo.itemData.return_value = "idx2"
    IndexCombo.on_combo_change(widget, 3)
    assert widget.current_id == "idx2"
    widget.window.controller.idx.select_by_id.assert_called_once_with("idx2")


def test_current_project_group_only_applies_to_virtual_index():
    widget = _widget(current="normal")
    assert IndexCombo._current_project_group_id(widget) is None
    widget.window.core.idx.project.get_current_group_id.assert_not_called()
    widget.current_id = "virtual"
    assert IndexCombo._current_project_group_id(widget) == "g1"


def test_index_combo_regular_actions_route_to_context_indexer():
    widget = _widget(current="idx")
    IndexCombo.action_idx_db_all(widget)
    IndexCombo.action_idx_db_update(widget)
    IndexCombo.action_idx_files_all(widget)
    IndexCombo.action_clear(widget)
    IndexCombo.action_truncate(widget)
    idx = widget.window.controller.idx.indexer
    idx.index_ctx_from_ts.assert_called_once_with("idx", 0)
    idx.index_ctx_current.assert_called_once_with("idx")
    idx.index_all_files.assert_called_once_with("idx")
    idx.clear.assert_called_once_with("idx")
    idx.truncate.assert_called_once_with("idx")


def test_index_combo_virtual_actions_route_to_project_indexer():
    widget = _widget(current="virtual", group="project-7")
    IndexCombo.action_idx_db_all(widget)
    IndexCombo.action_idx_db_update(widget)
    IndexCombo.action_clear(widget)
    IndexCombo.action_truncate(widget)
    idx = widget.window.controller.idx.indexer
    idx.index_project.assert_any_call("project-7", from_last=False)
    idx.index_project.assert_any_call("project-7", from_last=True)
    assert idx.truncate_project.call_count == 2
    idx.truncate_project.assert_called_with("project-7")
    idx.index_ctx_from_ts.assert_not_called()
    idx.index_ctx_current.assert_not_called()
    idx.clear.assert_not_called()
    idx.truncate.assert_not_called()


def test_index_combo_none_current_id_makes_mutating_actions_noop():
    widget = _widget(current=None)
    IndexCombo.action_idx_db_all(widget)
    IndexCombo.action_idx_db_update(widget)
    IndexCombo.action_idx_files_all(widget)
    IndexCombo.action_edit(widget)
    IndexCombo.action_clear(widget)
    IndexCombo.action_truncate(widget)
    idx = widget.window.controller.idx.indexer
    for mock in vars(idx).values():
        if isinstance(mock, MagicMock):
            mock.assert_not_called()
    widget.window.controller.settings.open_section.assert_not_called()


def test_index_combo_edit_opens_llama_index_settings_for_selected_index():
    widget = _widget(current="idx")
    IndexCombo.action_edit(widget)
    widget.window.controller.settings.open_section.assert_called_once_with("llama-index")
