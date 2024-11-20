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

from unittest.mock import MagicMock

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
    mock_window.ui.models['indexes'].index = MagicMock(return_value=1)
    mock_window.ui.nodes['indexes'].setCurrentIndex = MagicMock()
    idx.select_current()


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
    """Test update list"""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.list", [])
    mock_window.ui.toolbox.indexes.update = MagicMock()
    idx.update_list()
    mock_window.ui.toolbox.indexes.update.assert_called_once_with([])


def test_on_ctx_end(mock_window):
    """Test on ctx end"""
    idx = Idx(mock_window)
    mock_window.controller.kernel.stopped = MagicMock(return_value=False)
    mock_window.core.config.set("llama.idx.auto", True)
    mock_window.core.config.set("llama.idx.auto.index", "base")
    mock_window.controller.chat.input.stop = False
    idx.indexer.index_ctx_realtime = MagicMock()
    idx.on_ctx_end()
    idx.indexer.index_ctx_realtime.assert_called_once()


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
    idx.refresh()
    idx.select_default.assert_called_once()


def test_change_locked(mock_window):
    """Test change locked"""
    idx = Idx(mock_window)
    res = idx.change_locked()
    assert res is False
