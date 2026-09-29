from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from pygpt_net.item.store import RemoteFileItem
from pygpt_net.provider.core.remote_file.db_sqlite.provider import DbSqliteProvider


def make_window():
    return SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())))


def provider():
    p = DbSqliteProvider(make_window())
    p.storage = MagicMock()
    p.patcher = MagicMock()
    return p


def test_attach_patch_create_id_and_create():
    p = provider(); window = make_window()
    p.attach(window); p.storage.attach.assert_called_once_with(window)
    version = Version("2.8.0"); p.patcher.execute.return_value = True
    assert p.patch(version) is True
    with patch("pygpt_net.provider.core.remote_file.db_sqlite.provider.uuid.uuid4", return_value="uuid"):
        assert p.create_id() == "uuid"
    item = RemoteFileItem(); p.create_id = MagicMock(return_value="generated"); p.storage.insert.return_value = 5
    assert p.create(item) == 5
    assert item.uuid == "generated"
    p.storage.insert.assert_called_once_with(item)
    p.storage.insert.reset_mock(); item.record_id = 6
    assert p.create(item) == 6
    p.storage.insert.assert_not_called()


@pytest.mark.parametrize("method,args,target", [
    ("load_all", ("openai",), "get_all"),
    ("load", (1,), "get_by_id"),
    ("get_by_store_or_thread", ("store", "thread"), "get_by_store_or_thread"),
    ("count_by_store_or_thread", ("store", "thread"), "count_by_store_or_thread"),
    ("get_all_by_file_id", ("file",), "get_all_by_file_id"),
    ("delete_by_id", (1,), "delete_by_id"),
    ("delete_by_file_id", ("file",), "delete_by_file_id"),
    ("clear_store_from_files", ("store",), "clear_store_from_files"),
    ("clear_all_stores_from_files", ("openai",), "clear_all_stores_from_files"),
    ("rename_file", (1, "name.txt"), "rename_file"),
    ("truncate_all", ("openai",), "truncate_all"),
    ("truncate_by_store", ("store",), "truncate_by_store"),
])
def test_storage_delegates(method, args, target):
    p = provider(); expected = object()
    getattr(p.storage, target).return_value = expected
    assert getattr(p, method)(*args) is expected
    getattr(p.storage, target).assert_called_once_with(*args)


def test_save_and_save_all_handle_storage_errors():
    p = provider(); a = RemoteFileItem(); b = RemoteFileItem()
    p.save(a); p.storage.save.assert_called_once_with(a)
    p.storage.save.reset_mock(); p.save_all({"a": a, "b": b})
    assert p.storage.save.call_count == 2
    p.storage.save.side_effect = RuntimeError("db")
    p.save(a)
    p.window.core.debug.log.assert_called()
