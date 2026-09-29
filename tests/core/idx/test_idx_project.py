#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.idx import Idx
from pygpt_net.core.idx.project import Project
from tests.mocks import mock_window


def test_project_virtual_id_and_physical_id(mock_window):
    provider = MagicMock()
    project = Project(mock_window, provider)

    assert project.VIRTUAL_ID == "__project__"
    assert project.get_idx_id(12) == "proj_12"
    assert project.is_virtual("__project__") is True
    assert project.is_project_idx("proj_12") is True
    assert project.is_project_idx("base") is False
    assert project.get_group_id_from_idx("proj_12") == 12
    assert project.get_group_id_from_idx("base") is None


def test_project_resolve_current_project(mock_window):
    provider = MagicMock()
    project = Project(mock_window, provider)
    mock_window.core.ctx.get_current_meta = MagicMock(
        return_value=SimpleNamespace(group_id=23)
    )

    assert project.resolve("__project__") == "proj_23"
    assert project.resolve("base") == "base"


def test_project_resolve_virtual_without_project_returns_none(mock_window):
    provider = MagicMock()
    project = Project(mock_window, provider)
    mock_window.core.ctx.get_current_meta = MagicMock(return_value=None)

    assert project.resolve("__project__") is None


def test_project_ensure_creates_tracking_row_only_once(mock_window):
    provider = MagicMock()
    provider.get_project = MagicMock(side_effect=[None, {"group_id": 5}])
    provider.upsert_project = MagicMock(return_value=True)
    project = Project(mock_window, provider)

    assert project.ensure(5) is True
    provider.upsert_project.assert_called_once_with(5, "proj_5", 0, 0, 0)

    provider.upsert_project.reset_mock()
    assert project.ensure(5) is True
    provider.upsert_project.assert_not_called()


def test_project_touch_updates_incremental_cursor(mock_window):
    provider = MagicMock()
    provider.upsert_project = MagicMock(return_value=True)
    project = Project(mock_window, provider)

    assert project.touch(8, 101, 202) is True

    args = provider.upsert_project.call_args.args
    assert args[:4] == (8, "proj_8", 101, 202)
    assert isinstance(args[4], int) and args[4] > 0


def test_core_resolves_virtual_project_index(mock_window):
    idx = Idx(mock_window)
    mock_window.core.ctx.get_current_meta = MagicMock(
        return_value=SimpleNamespace(group_id=17)
    )

    assert idx.resolve_idx("__project__") == "proj_17"
    assert idx.get_current_project_idx(virtual=True) == "__project__"
    assert idx.get_current_project_idx(virtual=False) == "proj_17"


def test_get_file_index_status_hides_physical_current_project_id(mock_window):
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    mock_window.core.ctx.get_current_meta = MagicMock(
        return_value=SimpleNamespace(group_id=7)
    )
    idx.files.get_id = MagicMock(return_value="docs/a.txt")
    idx.files.get_status = MagicMock(return_value=[
        {"idx": "base", "updated_ts": 100},
        {"idx": "proj_7", "updated_ts": 200},
    ])

    status = idx.get_file_index_status("/tmp/docs/a.txt")

    assert status["indexed"] is True
    assert status["global_indexes"] == ["base"]
    assert status["project_indexes"] == ["proj_7"]
    assert "base" in status["indexed_in"]
    assert "proj_7" not in status["indexed_in"]
    assert status["last_index_at"] == 200


def test_index_project_uses_last_item_cursor(mock_window):
    idx = Idx(mock_window)
    idx.project.get = MagicMock(return_value={"last_item": 55})
    idx.project.touch = MagicMock(return_value=True)
    idx.storage.exists = MagicMock(return_value=True)
    idx.storage.get = MagicMock(return_value="INDEX")
    idx.storage.store = MagicMock()
    idx.llm.get_service_context = MagicMock(return_value=("LLM", "EMBED"))
    idx.indexing.index_db_project = MagicMock(return_value=(3, [], 11, 88))

    num, errors = idx.index_project(4, from_last=True)

    assert num == 3
    assert errors == []
    idx.indexing.index_db_project.assert_called_once_with(
        idx="proj_4", index="INDEX", group_id=4, last_item=55
    )
    idx.storage.store.assert_called_once_with(id="proj_4", index="INDEX")
    idx.project.touch.assert_called_once_with(4, 11, 88)


def test_index_project_resets_stale_cursor_when_storage_missing(mock_window):
    idx = Idx(mock_window)
    idx.project.get = MagicMock(return_value={"last_item": 55})
    idx.storage.exists = MagicMock(return_value=False)
    idx.storage.get = MagicMock(return_value="INDEX")
    idx.llm.get_service_context = MagicMock(return_value=("LLM", "EMBED"))
    idx.indexing.index_db_project = MagicMock(return_value=(0, [], 0, 0))

    idx.index_project(4, from_last=True)

    assert idx.indexing.index_db_project.call_args.kwargs["last_item"] == 0


def test_index_project_full_rebuild_truncates_old_project_index(mock_window):
    idx = Idx(mock_window)
    idx.project.get = MagicMock(return_value={"last_item": 55})
    idx.project.remove_state = MagicMock(return_value=True)
    idx.project.ensure = MagicMock(return_value=True)
    idx.storage.exists = MagicMock(return_value=True)
    idx.storage.get = MagicMock(return_value="INDEX")
    idx.remove_index = MagicMock(return_value=True)
    idx.llm.get_service_context = MagicMock(return_value=("LLM", "EMBED"))
    idx.indexing.index_db_project = MagicMock(return_value=(0, [], 0, 0))

    idx.index_project(4, from_last=False)

    idx.remove_index.assert_called_once_with("proj_4", truncate=True)
    idx.project.remove_state.assert_called_once_with(4)
    assert idx.indexing.index_db_project.call_args.kwargs["last_item"] == 0
    idx.project.ensure.assert_called_once_with(4)


def test_truncate_project_always_removes_tracking_state(mock_window):
    idx = Idx(mock_window)
    idx.get_provider().get_index_stores = MagicMock(return_value=[])
    idx.get_current_store = MagicMock(return_value="test_store")
    idx.remove_index = MagicMock(side_effect=RuntimeError("storage failure"))
    idx.project.remove_state = MagicMock(return_value=True)

    # Truncation is best-effort: storage errors are logged and reported via
    # False, while tracking state must still be removed in the finally block.
    assert idx.truncate_project(9) is False

    idx.remove_index.assert_called_once_with(
        "proj_9", truncate=True, store_id="test_store"
    )
    idx.project.remove_state.assert_called_once_with(9)
    mock_window.core.debug.log.assert_called_once()
