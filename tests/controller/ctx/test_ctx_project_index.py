#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.ctx.ctx import Ctx
from tests.mocks import mock_window


def test_update_project_index_delegates_to_incremental_indexer(mock_window):
    controller = Ctx(mock_window)
    mock_window.controller.idx.indexer.index_project = MagicMock()

    controller.update_project_index(12)

    mock_window.controller.idx.indexer.index_project.assert_called_once_with(
        12, from_last=True, sync=False, silent=False
    )


def test_truncate_project_index_opens_confirmation_flow(mock_window):
    controller = Ctx(mock_window)
    mock_window.controller.idx.indexer.truncate_project = MagicMock()

    controller.truncate_project_index(12)

    mock_window.controller.idx.indexer.truncate_project.assert_called_once_with(12, False)


def test_delete_group_truncates_project_index_before_removing_group(mock_window):
    controller = Ctx(mock_window)
    group = SimpleNamespace(id=12, name="Project")
    mock_window.core.ctx.get_group_by_id = MagicMock(return_value=group)
    mock_window.core.idx.truncate_project = MagicMock(return_value=True)
    mock_window.core.ctx.remove_group = MagicMock()
    controller.update_and_restore = MagicMock()
    controller.group_id = 12

    controller.delete_group(12, force=True)

    mock_window.core.idx.truncate_project.assert_called_once_with(12)
    mock_window.core.ctx.remove_group.assert_called_once_with(group, all=False)
    assert controller.group_id is None
    controller.update_and_restore.assert_called_once()


def test_delete_group_still_removes_group_when_project_truncate_fails(mock_window):
    controller = Ctx(mock_window)
    group = SimpleNamespace(id=12, name="Project")
    mock_window.core.ctx.get_group_by_id = MagicMock(return_value=group)
    mock_window.core.idx.truncate_project = MagicMock(side_effect=RuntimeError("broken index"))
    mock_window.core.ctx.remove_group = MagicMock()
    mock_window.core.debug.log = MagicMock()
    controller.update_and_restore = MagicMock()

    controller.delete_group(12, force=True)

    mock_window.core.debug.log.assert_called_once()
    mock_window.core.ctx.remove_group.assert_called_once_with(group, all=False)
    controller.update_and_restore.assert_called_once()


def _prepare_duplicate(mock_window, source_has_index):
    group = SimpleNamespace(id=4, name="Project")
    mock_window.core.ctx.get_group_by_id = MagicMock(return_value=group)
    mock_window.core.ctx.make_group = MagicMock(return_value=SimpleNamespace(name="Project (copy)"))
    mock_window.core.ctx.insert_group = MagicMock(return_value=9)
    mock_window.core.ctx.get_meta = MagicMock(return_value={})
    mock_window.core.idx.project.get_idx_id = MagicMock(return_value="proj_4")
    mock_window.core.idx.project.get = MagicMock(
        return_value={"group_id": 4} if source_has_index else None
    )
    mock_window.core.idx.storage.exists = MagicMock(return_value=source_has_index)
    mock_window.controller.idx.indexer.duplicate_project_index = MagicMock()


def test_duplicate_group_rebuilds_project_index_when_source_has_one(mock_window):
    controller = Ctx(mock_window)
    controller.update_and_restore = MagicMock()
    _prepare_duplicate(mock_window, source_has_index=True)

    controller.duplicate_group(4)

    mock_window.controller.idx.indexer.duplicate_project_index.assert_called_once_with(
        4, 9, silent=True
    )
    assert controller.group_id == 9


def test_duplicate_group_does_not_create_empty_project_index(mock_window):
    controller = Ctx(mock_window)
    controller.update_and_restore = MagicMock()
    _prepare_duplicate(mock_window, source_has_index=False)

    controller.duplicate_group(4)

    mock_window.controller.idx.indexer.duplicate_project_index.assert_not_called()
    assert controller.group_id == 9
