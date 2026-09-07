from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.lists.index import IndexList
from pygpt_net.ui.widget.lists.model import ModelList
from pygpt_net.ui.widget.lists.mode import ModeList
from pygpt_net.ui.widget.lists.plugin import PluginList
from pygpt_net.ui.widget.lists.settings import SettingsSectionList


def _event_for_row(row):
    event = MagicMock()
    index = MagicMock()
    index.row.return_value = row
    widget = SimpleNamespace(indexAt=MagicMock(return_value=index), window=MagicMock())
    return widget, event


def test_index_click_selects_row():
    widget = SimpleNamespace(window=MagicMock())
    value = MagicMock()
    value.row.return_value = 3
    IndexList.click(widget, value)
    widget.window.controller.idx.select.assert_called_once_with(3)


@pytest.mark.parametrize(
    "method,target",
    [
        (IndexList.action_idx_db_all, "idx_db_all_by_idx"),
        (IndexList.action_idx_db_update, "idx_db_update_by_idx"),
        (IndexList.action_idx_files_all, "idx_files_all_by_idx"),
    ],
)
def test_index_actions_dispatch_selected_row(method, target):
    widget, event = _event_for_row(4)
    method(widget, event)
    getattr(widget.window.controller.idx, target).assert_called_once_with(4)


def test_index_edit_clear_and_truncate_dispatch_selected_row():
    widget, event = _event_for_row(2)

    IndexList.action_edit(widget, event)
    IndexList.action_clear(widget, event)
    IndexList.action_truncate(widget, event)

    widget.window.controller.settings.open_section.assert_called_once_with("llama-index")
    widget.window.controller.idx.indexer.clear_by_idx.assert_called_once_with(2)
    widget.window.controller.idx.indexer.truncate_by_idx.assert_called_once_with(2)


def test_index_actions_ignore_invalid_row():
    widget, event = _event_for_row(-1)
    IndexList.action_clear(widget, event)
    IndexList.action_truncate(widget, event)
    widget.window.controller.idx.indexer.clear_by_idx.assert_not_called()
    widget.window.controller.idx.indexer.truncate_by_idx.assert_not_called()


def test_model_list_click_and_edit():
    selection_model = MagicMock()
    selection_model.selection.return_value = "selection"
    widget = SimpleNamespace(window=MagicMock(), selection=None, selectionModel=lambda: selection_model)
    value = MagicMock()
    value.row.return_value = 5

    ModelList.click(widget, value)
    assert widget.selection == "selection"
    widget.window.controller.model.select.assert_called_once_with(5)

    event = MagicMock()
    index = MagicMock()
    index.row.return_value = 5
    widget.indexAt = MagicMock(return_value=index)
    ModelList.action_edit(widget, event)
    widget.window.controller.model.editor.open_by_idx.assert_called_once_with(5)


def test_settings_and_plugin_lists_switch_matching_tab():
    settings = SimpleNamespace(window=MagicMock())
    plugin = SimpleNamespace(window=MagicMock())
    value = MagicMock()
    value.row.return_value = 2

    SettingsSectionList.click(settings, value)
    PluginList.click(plugin, value)

    settings.window.ui.tabs["settings.section"].setCurrentIndex.assert_called_once_with(2)
    settings.window.controller.settings.set_by_tab.assert_called_once_with(2)
    plugin.window.ui.tabs["plugin.settings"].setCurrentIndex.assert_called_once_with(2)
    plugin.window.controller.plugins.set_by_tab.assert_called_once_with(2)


def test_mode_list_click_only_updates_selection_snapshot():
    selection_model = MagicMock()
    selection_model.selection.return_value = "snapshot"
    widget = SimpleNamespace(selection=None, selectionModel=lambda: selection_model)

    ModeList.click(widget, MagicMock())
    assert widget.selection == "snapshot"
