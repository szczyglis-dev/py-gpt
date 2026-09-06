from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from pygpt_net.item.store import RemoteStoreItem
from pygpt_net.provider.core.remote_store.db_sqlite.provider import DbSqliteProvider


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
    with patch("pygpt_net.provider.core.remote_store.db_sqlite.provider.uuid.uuid4", return_value="uuid"):
        assert p.create_id() == "uuid"
    item = RemoteStoreItem(); p.create_id = MagicMock(return_value="generated"); p.storage.insert.return_value = 4
    assert p.create(item) == 4
    assert item.uuid == "generated"
    p.storage.insert.assert_called_once_with(item)
    p.storage.insert.reset_mock(); item.record_id = 9
    assert p.create(item) == 9
    p.storage.insert.assert_not_called()


@pytest.mark.parametrize("method,args,target", [
    ("load_all", ("openai",), "get_all"),
    ("load", (1,), "get_by_id"),
    ("delete_by_id", (1,), "delete_by_id"),
    ("delete_by_store_id", ("vs_1",), "delete_by_store_id"),
    ("truncate", ("openai",), "truncate_all"),
])
def test_storage_delegates(method, args, target):
    p = provider(); expected = object()
    getattr(p.storage, target).return_value = expected
    assert getattr(p, method)(*args) is expected
    getattr(p.storage, target).assert_called_once_with(*args)


def test_save_and_save_all_handle_storage_errors():
    p = provider(); a = RemoteStoreItem(); b = RemoteStoreItem()
    p.save(a); p.storage.save.assert_called_once_with(a)
    p.storage.save.reset_mock(); p.save_all({"a": a, "b": b})
    assert p.storage.save.call_count == 2
    p.storage.save.side_effect = RuntimeError("db")
    p.save(a)
    p.window.core.debug.log.assert_called()
