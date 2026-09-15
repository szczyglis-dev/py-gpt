#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

import pytest

from tests.mocks import mock_window
from pygpt_net.controller.idx.indexer import Indexer


def test_update_explorer(mock_window):
    """Test update explorer"""
    mock_window.controller.files.update_explorer = MagicMock()
    idx = Indexer(mock_window)
    idx.update_explorer()
    mock_window.controller.files.update_explorer.assert_called_once()


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
    """Current-context indexing uses the cursor scoped to store + index."""
    mock_window.update_status = MagicMock()
    mock_window.core.idx.resolve_idx = MagicMock(return_value="base")
    mock_window.core.idx.get_current_store = MagicMock(return_value="test_store")
    mock_window.core.idx.ctx.get_updated_ts = MagicMock(return_value=12345)
    idx = Indexer(mock_window)
    idx.index_ctx_from_ts = MagicMock()

    idx.index_ctx_current("base")

    mock_window.core.idx.ctx.get_updated_ts.assert_called_once_with("test_store", "base")
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
    """File indexing resolves the runtime index before dispatching the job."""
    mock_window.update_status = MagicMock()
    mock_window.core.idx.resolve_idx = MagicMock(return_value="base")
    idx = Indexer(mock_window)
    idx.index_path = MagicMock()

    idx.index_file("file.txt", "base", True)

    mock_window.core.idx.resolve_idx.assert_called_once_with("base")
    idx.index_path.assert_called_once_with("file.txt", "base", show_loader=False)


def test_clear_by_idx(mock_window):
    """Test clear by idx"""
    idx = Indexer(mock_window)
    idx.clear = MagicMock()
    mock_window.core.idx.get_by_idx = MagicMock(return_value="base")
    idx.clear_by_idx(12)
    idx.clear.assert_called_once_with("base")


def test_clear(mock_window):
    """Clear resolves an index and removes both storage and local tracking."""
    mock_window.update_status = MagicMock()
    mock_window.core.idx.resolve_idx = MagicMock(return_value="base")
    mock_window.core.idx.clear = MagicMock()
    mock_window.core.idx.remove_index = MagicMock(return_value=True)
    idx = Indexer(mock_window)
    idx.update_explorer = MagicMock()

    idx.clear("base", True)

    mock_window.core.idx.remove_index.assert_called_once_with("base")
    mock_window.core.idx.clear.assert_called_once_with("base")
    idx.update_explorer.assert_called_once()


def test_resolve_idx_virtual_project(mock_window):
    """The controller resolves __project__ before a worker is queued."""
    mock_window.core.idx.resolve_idx = MagicMock(return_value="proj_9")
    mock_window.core.idx.project.is_virtual = MagicMock(return_value=True)
    idx = Indexer(mock_window)

    assert idx.resolve_idx("__project__") == "proj_9"


def test_resolve_idx_virtual_project_outside_project_raises(mock_window):
    """Using __project__ without an active project fails explicitly."""
    mock_window.core.idx.resolve_idx = MagicMock(return_value=None)
    mock_window.core.idx.project.is_virtual = MagicMock(return_value=True)
    idx = Indexer(mock_window)

    with pytest.raises(RuntimeError, match="outside a project"):
        idx.resolve_idx("__project__")


def test_index_project_queues_project_worker(mock_window):
    """Project updates use a dedicated db_project worker and physical proj_<id> index."""
    mock_window.core.idx.project.get_idx_id = MagicMock(return_value="proj_12")
    mock_window.threadpool.start = MagicMock()
    idx = Indexer(mock_window)

    idx.index_project(12, from_last=True, sync=False, silent=True)

    worker = mock_window.threadpool.start.call_args.args[0]
    assert worker.type == "db_project"
    assert worker.content == 12
    assert worker.idx == "proj_12"
    assert worker.replace is True
    assert worker.silent is True


def test_truncate_project_requires_confirmation(mock_window):
    """Truncating one project asks for confirmation before destructive work."""
    idx = Indexer(mock_window)

    idx.truncate_project(15, force=False)

    kwargs = mock_window.ui.dialogs.confirm.call_args.kwargs
    assert kwargs["type"] == "idx.project.truncate"
    assert kwargs["id"] == 15
    mock_window.core.idx.truncate_project.assert_not_called()


def test_truncate_project_force_removes_project_index(mock_window):
    """Confirmed project truncation delegates to the core and refreshes the UI."""
    mock_window.core.idx.truncate_project = MagicMock(return_value=True)
    mock_window.controller.ctx.update_and_restore = MagicMock()
    idx = Indexer(mock_window)
    idx.update_explorer = MagicMock()

    idx.truncate_project(15, force=True)

    mock_window.core.idx.truncate_project.assert_called_once_with(15)
    idx.update_explorer.assert_called_once()
    mock_window.controller.ctx.update_and_restore.assert_called_once()


def test_truncate_projects_force_removes_all_project_indexes(mock_window):
    """Confirmed batch truncation delegates to the project-index registry cleanup."""
    mock_window.core.idx.truncate_projects = MagicMock(return_value=True)
    mock_window.controller.ctx.update_and_restore = MagicMock()
    idx = Indexer(mock_window)
    idx.update_explorer = MagicMock()

    idx.truncate_projects(force=True)

    mock_window.core.idx.truncate_projects.assert_called_once()
    idx.update_explorer.assert_called_once()
    mock_window.controller.ctx.update_and_restore.assert_called_once()


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