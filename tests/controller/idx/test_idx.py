#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 01:00:00                  #
# ================================================== #

from types import SimpleNamespace
from unittest.mock import MagicMock, call

from tests.mocks import mock_window
from pygpt_net.controller.idx import Idx


def test_setup(mock_window):
    """Test setup"""
    mock_window.core.idx.load = MagicMock()
    idx = Idx(mock_window)
    idx.indexer.update_explorer = MagicMock()
    idx.common.setup = MagicMock()
    idx.update = MagicMock()
    idx.setup()
    mock_window.core.idx.load.assert_called_once()
    idx.indexer.update_explorer.assert_called_once()
    idx.common.setup.assert_called_once()
    idx.update.assert_called_once()


def test_select(mock_window):
    """Test select"""
    idx = Idx(mock_window)
    idx.change_locked = MagicMock(return_value=False)
    idx.set_by_idx = MagicMock()
    mock_window.controller.ui.update = MagicMock()
    idx.select(1)
    idx.set_by_idx.assert_called_once_with(1)


def test_set(mock_window):
    """Test set"""
    idx = Idx(mock_window)
    idx.set("base")
    assert idx.current_idx == "base"
    assert mock_window.core.config.get('llama.idx.current') == "base"


def test_idx_db_update_by_idx(mock_window):
    """Test idx db update by idx"""
    mock_window.core.idx.get_by_idx = MagicMock(return_value="base")
    idx = Idx(mock_window)
    idx.indexer.index_ctx_current = MagicMock()
    idx.idx_db_update_by_idx(1)
    idx.indexer.index_ctx_current.assert_called_once_with("base")


def test_idx_db_all_by_idx(mock_window):
    """Test idx db all by idx"""
    mock_window.core.idx.get_by_idx = MagicMock(return_value="base")
    idx = Idx(mock_window)
    idx.indexer.index_ctx_from_ts = MagicMock()
    idx.idx_db_all_by_idx(1)
    idx.indexer.index_ctx_from_ts.assert_called_once_with("base", 0)


def test_idx_files_all_by_idx(mock_window):
    """Test idx files all by idx"""
    mock_window.core.idx.get_by_idx = MagicMock(return_value="base")
    idx = Idx(mock_window)
    idx.indexer.index_all_files = MagicMock()
    idx.idx_files_all_by_idx(1)
    idx.indexer.index_all_files.assert_called_once_with("base")


def test_set_by_idx(mock_window):
    """Test set by idx"""
    mock_window.core.idx.get_by_idx = MagicMock(return_value="base")
    idx = Idx(mock_window)
    idx.set_by_idx(1)
    assert idx.current_idx == "base"
    assert mock_window.core.config.get('llama.idx.current') == "base"


def test_select_current(mock_window):
    """Test select current"""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.current", "base")
    items = []
    mock_window.core.config.set("llama.idx.list", items)
    mock_window.core.idx.get_idx_by_name = MagicMock(return_value="base")
    node = mock_window.ui.nodes['indexes.select']
    # Idx._sync_combo() resolves the selector through ui.nodes.get(), while
    # MagicMock's __getitem__ and get() return different child mocks by default.
    # Make both access paths point at the same selector instance.
    mock_window.ui.nodes.get.return_value = node
    node.has_key = MagicMock(return_value=True)
    node.combo.findData = MagicMock(return_value=1)
    node.combo.blockSignals = MagicMock(return_value=False)
    idx.select_current()
    node.combo.setCurrentIndex.assert_called_once_with(1)
    assert node.current_id == 'base'


def test_select_default(mock_window):
    """Test select default"""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.current", "base")
    mock_window.core.idx.get_default_idx = MagicMock(return_value="base")
    idx.select_default()
    assert idx.current_idx == "base"


def test_update(mock_window):
    """Test update"""
    idx = Idx(mock_window)
    idx.select_default = MagicMock()
    idx.update_list = MagicMock()
    idx.select_current = MagicMock()
    idx.update()
    idx.select_default.assert_called_once()
    idx.update_list.assert_called_once()
    idx.select_current.assert_called_once()


def test_update_list(mock_window):
    """Global index list stays unchanged outside a project."""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.list", [])
    mock_window.core.idx.project.get_current_group_id = MagicMock(return_value=None)
    mock_window.ui.toolbox.indexes.update = MagicMock()
    idx.update_list()
    mock_window.ui.toolbox.indexes.update.assert_called_once_with([])


def test_update_list_injects_current_project_without_physical_id(mock_window):
    """The runtime project entry is injected only while a project is active."""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.list", [{"id": "base", "name": "Base"}])
    mock_window.core.idx.project.get_current_group_id = MagicMock(return_value=7)
    mock_window.core.idx.project.VIRTUAL_ID = "__project__"
    mock_window.ui.toolbox.indexes.update = MagicMock()

    idx.update_list()

    items = mock_window.ui.toolbox.indexes.update.call_args.args[0]
    assert items[0]["id"] == "__project__"
    assert "__project__" not in items[0]["name"]
    assert items[1] == {"id": "base", "name": "Base"}


def _prepare_auto_index(mock_window, *, policy="all", group_id=0, isolated=True, targets="base"):
    meta = SimpleNamespace(id=10, group_id=group_id)
    mock_window.controller.kernel.stopped = MagicMock(return_value=False)
    mock_window.core.config.set("llama.idx.auto", policy)
    mock_window.core.config.set("llama.idx.auto.project", isolated)
    mock_window.core.config.set("llama.idx.auto.index", targets)
    mock_window.core.config.set("llama.idx.auto.modes", "chat,agent")
    mock_window.core.ctx.get_current_meta = MagicMock(return_value=meta)
    mock_window.core.ctx.get_meta_by_id = MagicMock(return_value=meta)
    return meta


def test_on_ctx_end_auto_index_all_global(mock_window):
    """Policy=all indexes a non-project conversation into all global targets."""
    idx = Idx(mock_window)
    meta = _prepare_auto_index(mock_window, targets="base,docs")
    idx.indexer.index_ctx_realtime = MagicMock()
    idx.indexer.index_project = MagicMock()

    idx.on_ctx_end(mode="chat")

    assert idx.indexer.index_ctx_realtime.call_args_list == [
        call(meta, "base", sync=False),
        call(meta, "docs", sync=False),
    ]
    idx.indexer.index_project.assert_not_called()


def test_on_ctx_end_auto_index_off(mock_window):
    """Policy=off disables conversation auto-indexing completely."""
    idx = Idx(mock_window)
    _prepare_auto_index(mock_window, policy="off")
    idx.indexer.index_ctx_realtime = MagicMock()
    idx.indexer.index_project = MagicMock()

    idx.on_ctx_end(mode="chat")

    idx.indexer.index_ctx_realtime.assert_not_called()
    idx.indexer.index_project.assert_not_called()


def test_on_ctx_end_projects_policy_skips_global_conversation(mock_window):
    """Policy=projects ignores conversations outside projects."""
    idx = Idx(mock_window)
    _prepare_auto_index(mock_window, policy="projects", group_id=0)
    idx.indexer.index_ctx_realtime = MagicMock()
    idx.indexer.index_project = MagicMock()

    idx.on_ctx_end(mode="chat")

    idx.indexer.index_ctx_realtime.assert_not_called()
    idx.indexer.index_project.assert_not_called()


def test_on_ctx_end_uses_isolated_project_index(mock_window):
    """An active project is routed exclusively to proj_<group> when isolation is enabled."""
    idx = Idx(mock_window)
    _prepare_auto_index(mock_window, policy="all", group_id=42, isolated=True, targets="base")
    idx.indexer.index_ctx_realtime = MagicMock()
    idx.indexer.index_project = MagicMock()

    idx.on_ctx_end(mode="chat")

    idx.indexer.index_project.assert_called_once_with(42, from_last=True, sync=False, silent=True)
    idx.indexer.index_ctx_realtime.assert_not_called()


def test_on_ctx_end_project_can_use_global_indexes_when_isolation_disabled(mock_window):
    """Disabling project isolation keeps project conversations on configured global targets."""
    idx = Idx(mock_window)
    meta = _prepare_auto_index(mock_window, policy="all", group_id=42, isolated=False, targets="base,docs")
    idx.indexer.index_ctx_realtime = MagicMock()
    idx.indexer.index_project = MagicMock()

    idx.on_ctx_end(mode="chat")

    assert idx.indexer.index_ctx_realtime.call_args_list == [
        call(meta, "base", sync=False),
        call(meta, "docs", sync=False),
    ]
    idx.indexer.index_project.assert_not_called()


def test_on_ctx_end_legacy_bool_is_normalized_at_runtime(mock_window):
    """A legacy bool config still behaves correctly before the config patch is persisted."""
    idx = Idx(mock_window)
    meta = _prepare_auto_index(mock_window, policy=True, group_id=0, targets="base")
    idx.indexer.index_ctx_realtime = MagicMock()

    idx.on_ctx_end(mode="chat")

    idx.indexer.index_ctx_realtime.assert_called_once_with(meta, "base", sync=False)


def test_after_index(mock_window):
    """Test after index"""
    idx = Idx(mock_window)
    idx.indexer.update_explorer = MagicMock()
    mock_window.ui.nodes['idx.db.last_updated'].setText = MagicMock()
    idx.after_index()
    idx.indexer.update_explorer.assert_called_once()
    mock_window.ui.nodes['idx.db.last_updated'].setText.assert_called_once()


def test_refresh(mock_window):
    """Test refresh"""
    idx = Idx(mock_window)
    idx.select_default = MagicMock()
    idx.update_list = MagicMock()
    idx.select_current = MagicMock()
    mock_window.controller.presets.editor.opened = False
    idx.refresh()
    idx.select_default.assert_called_once()
    idx.update_list.assert_called_once()
    idx.select_current.assert_called_once()


def test_change_locked(mock_window):
    """Test change locked"""
    idx = Idx(mock_window)
    res = idx.change_locked()
    assert res is False
