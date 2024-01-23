#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.idx.indexer import Indexer


def test_update_explorer(mock_window):
    """Test update explorer"""
    mock_window.core.idx.load = MagicMock()
    idx = Indexer(mock_window)
    mock_window.core.idx.get_idx_data = MagicMock(return_value=[])
    mock_window.ui.nodes['output_files'].model.update_idx_status = MagicMock()
    idx.update_explorer()
    mock_window.ui.nodes['output_files'].model.update_idx_status.assert_called_once()


def test_update_idx_status(mock_window):
    """Test update idx status"""
    mock_window.core.idx.load = MagicMock()
    idx = Indexer(mock_window)
    idx.update_idx_status("base")
    assert mock_window.core.config.get('llama.idx.status')["base"] == {}
    assert mock_window.core.config.get('llama.idx.status')["last_ts"] > 0


def test_index_ctx_meta_confirm(mock_window):
    """Test index ctx meta confirm"""
    idx = Indexer(mock_window)
    idx.tmp_idx = "base"
    idx.index_ctx_meta = MagicMock()
    idx.index_ctx_meta_confirm(123)
    idx.index_ctx_meta.assert_called_once_with(123, "base", True)


def test_index_ctx_meta(mock_window):
    """Test index ctx meta"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    mock_window.core.ctx.get_id_by_idx = MagicMock(return_value=222)  # meta id
    mock_window.threadpool.start = MagicMock()
    idx.index_ctx_meta(123, "base", True)
    mock_window.threadpool.start.assert_called_once()


def test_index_ctx_current(mock_window):
    """Test index ctx current"""
    mock_window.update_status = MagicMock()
    mock_window.core.config.set("llama.idx.db.last", 12345)
    idx = Indexer(mock_window)
    idx.index_ctx_from_ts = MagicMock()
    mock_window.threadpool.start = MagicMock()
    idx.index_ctx_current("base")
    idx.index_ctx_from_ts.assert_called_once_with("base", 12345, force=False, silent=False)


def test_index_ctx_from_ts_confirm(mock_window):
    """Test index ctx from ts confirm"""
    idx = Indexer(mock_window)
    mock_window.update_status = MagicMock()
    idx.tmp_idx = "base"
    idx.index_ctx_from_ts = MagicMock()
    idx.index_ctx_from_ts_confirm(123)
    idx.index_ctx_from_ts.assert_called_once_with("base", 123, True)


def test_index_ctx_from_ts(mock_window):
    """Test index ctx from ts"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    mock_window.core.ctx.get_id_by_idx = MagicMock(return_value=222)  # meta id
    mock_window.threadpool.start = MagicMock()
    idx.index_ctx_from_ts("base", 123, True)
    mock_window.threadpool.start.assert_called_once()


def test_index_path(mock_window):
    """Test index path"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    mock_window.threadpool.start = MagicMock()
    idx.index_path("file.txt", "base")
    mock_window.threadpool.start.assert_called_once()


def test_index_all_files(mock_window):
    """Test index all files"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    idx.index_path = MagicMock()
    idx.index_all_files("file.txt", True)
    idx.index_path.assert_called_once()


def test_index_file_confirm(mock_window):
    """Test index file confirm"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    idx.tmp_idx = "base"
    idx.index_path = MagicMock()
    idx.index_file_confirm("file.txt")
    idx.index_path.assert_called_once()


def test_index_file(mock_window):
    """Test index file"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    idx.tmp_idx = "base"
    idx.index_path = MagicMock()
    idx.index_file("file.txt", "base", True)
    idx.index_path.assert_called_once_with("file.txt", "base")


def test_clear_by_idx(mock_window):
    """Test clear by idx"""
    idx = Indexer(mock_window)
    idx.clear = MagicMock()
    mock_window.core.idx.get_by_idx = MagicMock(return_value="base")
    idx.clear_by_idx(12)
    idx.clear.assert_called_once_with("base")


def test_clear(mock_window):
    """Test clear"""
    mock_window.update_status = MagicMock()
    mock_window.core.idx.clear = MagicMock()
    mock_window.core.idx.remove_index = MagicMock(return_value=True)
    idx = Indexer(mock_window)
    idx.update_explorer = MagicMock()
    idx.clear("base", True)
    mock_window.core.idx.clear.assert_called_once_with("base")
    idx.update_explorer.assert_called_once()


def test_handle_error(mock_window):
    """Test handle error"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    idx.handle_error("error")
    mock_window.update_status.assert_called_once_with("error")


def test_handle_finished_db_current(mock_window):
    """Test handle finished db current"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    idx.update_idx_status = MagicMock()
    mock_window.controller.idx.after_index = MagicMock()
    idx.handle_finished_db_current("base", 1, [], True)
    idx.update_idx_status.assert_called_once_with("base")
    mock_window.controller.idx.after_index.assert_called_once_with("base")


def test_handle_finished_db_meta(mock_window):
    """Test handle finished db meta"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    idx.update_idx_status = MagicMock()
    mock_window.controller.idx.after_index = MagicMock()
    idx.handle_finished_db_meta("base", 1, [], True)
    idx.update_idx_status.assert_called_once_with("base")
    mock_window.controller.idx.after_index.assert_called_once_with("base")


def test_handle_finished_file(mock_window):
    """Test handle finished file"""
    mock_window.update_status = MagicMock()
    idx = Indexer(mock_window)
    idx.update_idx_status = MagicMock()
    mock_window.core.idx.append = MagicMock()
    mock_window.controller.idx.after_index = MagicMock()
    files = {
        "file.txt": "id",
    }
    idx.handle_finished_file("base", files, [], True)
    idx.update_idx_status.assert_called_once_with("base")
    mock_window.core.idx.append.assert_called_once_with("base", files)
    mock_window.controller.idx.after_index.assert_called_once_with("base")