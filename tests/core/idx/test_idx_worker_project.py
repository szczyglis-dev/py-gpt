#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

from pygpt_net.core.idx.worker import IndexWorker
from tests.mocks import mock_window


def _worker(mock_window):
    worker = IndexWorker()
    worker.window = mock_window
    worker.signals = MagicMock()
    mock_window.core.config.set("log.llama", False)
    return worker


def test_worker_resolves_virtual_project_before_file_index(mock_window):
    worker = _worker(mock_window)
    signals = worker.signals
    worker.idx = "__project__"
    worker.type = "file"
    worker.content = "file.txt"
    worker.replace = False
    worker.recursive = False
    mock_window.core.idx.resolve_idx = MagicMock(return_value="proj_8")
    mock_window.core.idx.project.is_virtual = MagicMock(return_value=True)
    mock_window.core.idx.index_files = MagicMock(return_value=({"file.txt": "doc"}, []))

    worker.run()

    mock_window.core.idx.index_files.assert_called_once_with(
        "proj_8", "file.txt", False, False
    )
    signals.finished.emit.assert_called_once_with(
        "proj_8", {"file.txt": "doc"}, [], False
    )


def test_worker_db_project_uses_incremental_flag(mock_window):
    worker = _worker(mock_window)
    signals = worker.signals
    worker.idx = "proj_3"
    worker.type = "db_project"
    worker.content = 3
    worker.replace = True
    mock_window.core.idx.resolve_idx = MagicMock(return_value="proj_3")
    mock_window.core.idx.project.is_virtual = MagicMock(return_value=False)
    mock_window.core.idx.index_project = MagicMock(return_value=(2, []))

    worker.run()

    mock_window.core.idx.index_project.assert_called_once_with(3, from_last=True)
    signals.finished.emit.assert_called_once_with("proj_3", 2, [], False)


def test_worker_project_duplicate_routes_to_core(mock_window):
    worker = _worker(mock_window)
    signals = worker.signals
    worker.idx = "proj_9"
    worker.type = "project_duplicate"
    worker.content = (4, 9)
    mock_window.core.idx.resolve_idx = MagicMock(return_value="proj_9")
    mock_window.core.idx.project.is_virtual = MagicMock(return_value=False)
    mock_window.core.idx.duplicate_project_index = MagicMock(return_value=(5, []))

    worker.run()

    mock_window.core.idx.duplicate_project_index.assert_called_once_with(4, 9)
    signals.finished.emit.assert_called_once_with("proj_9", 5, [], False)


def test_worker_rejects_virtual_project_outside_project(mock_window):
    worker = _worker(mock_window)
    signals = worker.signals
    worker.idx = "__project__"
    worker.type = "file"
    worker.content = "file.txt"
    mock_window.core.idx.resolve_idx = MagicMock(return_value=None)
    mock_window.core.idx.project.is_virtual = MagicMock(return_value=True)

    worker.run()

    mock_window.core.idx.index_files.assert_not_called()
    signals.error.emit.assert_called_once()
    assert "outside a project" in str(signals.error.emit.call_args.args[0])
