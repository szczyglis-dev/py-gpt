from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.lists.preset_plugins import PresetPluginsList


def _widget(row):
    index = MagicMock(); index.row.return_value = row
    presets = SimpleNamespace(
        select_by_idx=MagicMock(), duplicate_by_idx=MagicMock(), reset_by_idx=MagicMock(),
        delete_by_idx=MagicMock(), rename_by_idx=MagicMock(),
    )
    return SimpleNamespace(
        indexAt=MagicMock(return_value=index),
        window=SimpleNamespace(controller=SimpleNamespace(plugins=SimpleNamespace(presets=presets))),
    )


@pytest.mark.parametrize("method,target", [
    (PresetPluginsList.action_use, "select_by_idx"),
    (PresetPluginsList.action_duplicate, "duplicate_by_idx"),
    (PresetPluginsList.action_reset, "reset_by_idx"),
    (PresetPluginsList.action_delete, "delete_by_idx"),
    (PresetPluginsList.action_rename, "rename_by_idx"),
])
def test_preset_plugin_actions_dispatch_valid_row(method, target):
    widget = _widget(3)
    method(widget, MagicMock())
    getattr(widget.window.controller.plugins.presets, target).assert_called_once_with(3)


@pytest.mark.parametrize("method,target", [
    (PresetPluginsList.action_use, "select_by_idx"),
    (PresetPluginsList.action_duplicate, "duplicate_by_idx"),
    (PresetPluginsList.action_reset, "reset_by_idx"),
    (PresetPluginsList.action_delete, "delete_by_idx"),
    (PresetPluginsList.action_rename, "rename_by_idx"),
])
def test_preset_plugin_actions_ignore_invalid_row(method, target):
    widget = _widget(-1)
    method(widget, MagicMock())
    getattr(widget.window.controller.plugins.presets, target).assert_not_called()
