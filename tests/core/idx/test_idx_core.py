#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.16 01:00:00                  #
# ================================================== #

import os
import platform
from unittest.mock import MagicMock

from packaging.version import Version

from pygpt_net.core.filesystem import Filesystem
from pygpt_net.item.index import IndexItem
from tests.mocks import mock_window
from pygpt_net.core.idx import Idx
from pygpt_net.core.idx.types.files import Files


def test_get_current_store(mock_window):
    """
    Test get current store name
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    assert idx.get_current_store() == "test_store"


def test_store_index(mock_window):
    """
    Test store index
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    idx.storage.store = MagicMock()
    idx.store_index()
    idx.storage.store.assert_called_once_with("base")


def test_remove_index(mock_window):
    """Removing an index clears all tracking rows and physical storage."""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    idx.ctx.truncate = MagicMock()
    idx.files.truncate = MagicMock()
    idx.external.truncate = MagicMock()
    mock_window.core.ctx.idx.truncate_indexed = MagicMock()
    idx.storage.exists = MagicMock(return_value=True)
    idx.storage.remove = MagicMock(return_value=True)

    assert idx.remove_index() is True

    idx.ctx.truncate.assert_called_once_with("test_store", "base")
    idx.files.truncate.assert_called_once_with("test_store", "base")
    idx.external.truncate.assert_called_once_with("test_store", "base")
    mock_window.core.ctx.idx.truncate_indexed.assert_called_once_with("test_store", "base")
    idx.storage.remove.assert_called_once_with("base")


def test_index_files(mock_window):
    """
    Test index file or directory of files
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    idx.llm.get_service_context = MagicMock(return_value=(MagicMock(), MagicMock()))
    index = MagicMock()
    idx.storage.get = MagicMock(return_value=index)
    idx.storage.store = MagicMock()
    files = {
        "file.txt": {
            "path": "%workdir%/data/file.txt",
            "indexed_ts": 1705822595.323048,
            "id": "61f210f3-5635-49b8-95f4-ebc998d53c2f"
        }
    }
    errors = []
    idx.indexing.index_files = MagicMock(return_value=(files, errors))
    f, e = idx.index_files(idx="base", path="file.txt")
    idx.storage.store.assert_called_once_with(id="base", index=index)
    assert f == files
    assert e == errors


def test_index_db_by_meta_id(mock_window):
    """
    Test index records from db by meta id
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    idx.llm.get_service_context = MagicMock(return_value=(MagicMock(), MagicMock()))
    index = MagicMock()
    idx.storage.get = MagicMock(return_value=index)
    idx.storage.store = MagicMock()
    num = 1
    errors = []
    idx.indexing.index_db_by_meta_id = MagicMock(return_value=(num, errors))
    n, e = idx.index_db_by_meta_id(idx="base", id=1)
    idx.storage.store.assert_called_once_with(id="base", index=index)
    assert n == num
    assert e == errors


def test_index_db_from_updated_ts(mock_window):
    """
    Test index records from db from updated timestamp
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    idx.llm.get_service_context = MagicMock(return_value=(MagicMock(), MagicMock()))
    index = MagicMock()
    idx.storage.get = MagicMock(return_value=index)
    idx.storage.store = MagicMock()
    num = 1
    errors = []
    idx.indexing.index_db_from_updated_ts = MagicMock(return_value=(num, errors))
    n, e = idx.index_db_from_updated_ts(idx="base", from_ts=1)
    idx.storage.store.assert_called_once_with(id="base", index=index)
    assert n == num
    assert e == errors


def test_get_idx_data(mock_window):
    """
    Test get index data
    """
    idx = Idx(mock_window)
    item = IndexItem()
    item.items = {
        "file.txt": {
            "path": "%workdir%/data/file.txt",
            "indexed_ts": 1705822595.323048,
            "id": "61f210f3-5635-49b8-95f4-ebc998d53c2f"
        }
    }
    mock_window.core.config.set("llama.idx.storage", "test_store")
    idx.items["test_store"] = {
        "base": item,
    }
    data = idx.get_idx_data(idx="base")
    assert data["base"] == item.items


def test_get_by_idx(mock_window):
    """
    Test get idx by list index
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        }
    ]
    mock_window.core.config.set("llama.idx.list", items)
    res = idx.get_by_idx(idx=0)
    assert res == "base"


def test_get_by_idx_not_found(mock_window):
    """
    Test get idx by list index not found
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        }
    ]
    mock_window.core.config.set("llama.idx.list", items)
    res = idx.get_by_idx(idx=1)
    assert res is None


def test_get_idx_by_name(mock_window):
    """
    Test get idx by name
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        },
        {
            "id": "base2",
            "name": "Base2"
        }
    ]
    mock_window.core.config.set("llama.idx.list", items)
    res = idx.get_idx_by_name(name="base2")
    assert res == 1


def test_get_default_idx(mock_window):
    """
    Test get default idx
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        },
        {
            "id": "base2",
            "name": "Base2"
        }
    ]
    idx.items = {
        "test_store": {
            "base": MagicMock(),
            "base2": MagicMock()
        }
    }
    mock_window.core.config.set("llama.idx.list", items)
    res = idx.get_default_idx()
    assert res == "base"


def test_install(mock_window):
    """
    Test install
    """
    idx = Idx(mock_window)
    idx.get_provider().install = MagicMock()
    idx.install()
    idx.get_provider().install.assert_called_once()


def test_patch(mock_window):
    """
    Test patch
    """
    idx = Idx(mock_window)
    idx.get_provider().patch = MagicMock()
    version = Version("1.0.0")
    idx.patch(version)
    idx.get_provider().patch.assert_called_once_with(version)


def test_init(mock_window):
    """
    Test init
    """
    idx = Idx(mock_window)
    idx.load = MagicMock()
    idx.init()
    idx.load.assert_called_once()


def test_get(mock_window):
    """
    Test get idx
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        },
    ]
    item = IndexItem()
    mock_window.core.config.set("llama.idx.list", items)
    idx.items = {
        "test_store": {
            "base": item,
        }
    }
    res = idx.get(idx="base")
    assert res == item


def test_get_all(mock_window):
    """
    Test get all idx
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        },
    ]
    item = IndexItem()
    mock_window.core.config.set("llama.idx.list", items)
    idx.items = {
        "test_store": {
            "base": item,
        }
    }
    res = idx.get_all()
    assert res == {
        "base": item
    }


def test_has(mock_window):
    """
    Test has idx
    """
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        },
    ]
    item = IndexItem()
    mock_window.core.config.set("llama.idx.list", items)
    idx.items = {
        "test_store": {
            "base": item,
        }
    }
    res = idx.has(idx="base")
    assert res is True


def test_to_file_id(mock_window):
    """
    Test to file id
    """
    provider = MagicMock()
    files = Files(mock_window, provider)
    root_dir = os.path.normpath(mock_window.core.config.get_user_dir('data'))
    mock_window.core.filesystem.get_data_dir = MagicMock(return_value=root_dir)

    if platform.system() == 'Windows':
        res = files.get_id(path=root_dir + "\\dir\\file.txt")
        assert res == "dir/file.txt"
    else:
        res = files.get_id(path=root_dir + "/dir/file.txt")
        assert res == "dir/file.txt"


def test_append(mock_window):
    """Appending indexed files writes lazy tracking rows without hydrating item contents."""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    item = IndexItem()
    idx.items = {"test_store": {"base": item}}
    idx.files.get_id = MagicMock(return_value="file.txt")
    idx.files.get_record = MagicMock(return_value=None)
    idx.files.append = MagicMock(return_value=1)

    idx.append(idx="base", files={
        "file.txt": "61f210f3-5635-49b8-95f4-ebc998d53c2f"
    })

    idx.files.append.assert_called_once_with(
        "test_store",
        "base",
        "file.txt",
        "file.txt",
        "61f210f3-5635-49b8-95f4-ebc998d53c2f",
    )
    assert idx.items["test_store"]["base"].items == {}


def test_append_updates_existing_lazy_tracking_row(mock_window):
    """Re-indexing a tracked file updates the existing DB row instead of duplicating it."""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    idx.files.get_id = MagicMock(return_value="file.txt")
    idx.files.get_record = MagicMock(return_value={"id": 77, "doc_id": "old"})
    idx.files.update = MagicMock(return_value=True)

    idx.append(idx="base", files={"file.txt": "new-doc"})

    args = idx.files.update.call_args.args
    assert args[0] == 77
    assert args[1] == "new-doc"
    assert isinstance(args[2], int) and args[2] > 0


def test_clear(mock_window):
    """
    Test clear
    """
    idx = Idx(mock_window)
    idx.save = MagicMock()
    mock_window.core.config.set("llama.idx.storage", "test_store")
    items = [
        {
            "id": "base",
            "name": "Base"
        },
    ]
    item = IndexItem()
    mock_window.core.config.set("llama.idx.list", items)
    idx.items = {
        "test_store": {
            "base": item,
        }
    }
    idx.clear(idx="base")
    assert idx.items["test_store"]["base"].items == {}


def test_load(mock_window):
    """Load hydrates only index identities; file contents stay lazy."""
    idx = Idx(mock_window)
    mock_window.core.config.set("llama.idx.storage", "test_store")
    mock_window.core.config.set("llama.idx.list", [{"id": "base", "name": "Base"}])
    idx.storage.get_ids = MagicMock(return_value=["test_store"])
    idx.get_provider().get_index_ids = MagicMock(return_value=["base"])
    idx.get_provider().load = MagicMock()

    idx.load()

    assert idx.items["test_store"]["base"].id == "base"
    assert idx.items["test_store"]["base"].items == {}
    idx.get_provider().get_index_ids.assert_called_once_with("test_store")
    idx.get_provider().load.assert_not_called()


def test_get_version(mock_window):
    """
    Test get_version
    """
    idx = Idx(mock_window)
    idx.get_provider().get_version = MagicMock(return_value="0.1.0")
    res = idx.get_version()
    assert res == "0.1.0"
