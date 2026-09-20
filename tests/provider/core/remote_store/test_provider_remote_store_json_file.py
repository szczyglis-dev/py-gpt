import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.item.store import RemoteStoreItem
from pygpt_net.provider.core.remote_store.json_file import JsonFileProvider


def make_window(path):
    return SimpleNamespace(core=SimpleNamespace(
        config=SimpleNamespace(path=str(path), append_meta=MagicMock(return_value={"v": 1})),
        debug=SimpleNamespace(log=MagicMock()),
    ))


def make_store(store_id="vs_1"):
    s = RemoteStoreItem()
    s.id = store_id
    s.uuid = "uuid"
    s.name = "Store"
    s.provider = "openai"
    s.description = "desc"
    s.status = {"file_counts": {"completed": 2}}
    s.last_status = "completed"
    s.expire_days = 7
    s.usage_bytes = 100
    s.bytes = 200
    s.num_files = 2
    s.is_thread = True
    s.created = 1_700_000_000
    s.updated = 1_700_000_100
    s.last_active = 1_700_000_200
    s.last_sync = 1_700_000_300
    s.file_ids = ["file-1", "file-2"]
    return s


def test_create_id_and_create(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    with patch("pygpt_net.provider.core.remote_store.json_file.uuid.uuid4", return_value="fixed"):
        s = RemoteStoreItem(); s.id = None
        assert provider.create(s) == "fixed"
    s.id = "existing"; provider.create_id = MagicMock()
    assert provider.create(s) == "existing"
    provider.create_id.assert_not_called()


def test_save_load_round_trip_and_noop_remove_truncate(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    s = make_store()
    provider.save({s.id: s})
    loaded = provider.load()
    assert loaded["vs_1"].name == "Store"
    assert loaded["vs_1"].status == s.status
    assert loaded["vs_1"].file_ids == ["file-1", "file-2"]
    assert provider.remove("vs_1") is None
    assert provider.truncate() is None
    assert "vs_1" in provider.load()


def test_load_handles_empty_and_invalid_payload(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    assert provider.load() == {}
    (tmp_path / provider.config_file).write_text("null", encoding="utf-8")
    assert provider.load() == {}
    (tmp_path / provider.config_file).write_text("{bad", encoding="utf-8")
    assert provider.load() == {}
    window.core.debug.log.assert_called_once()


def test_save_logs_write_error(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    with patch("builtins.open", side_effect=OSError("write")):
        provider.save({"x": make_store("x")})
    window.core.debug.log.assert_called_once()


def test_remove_and_truncate_are_explicit_noops(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    provider.save = MagicMock()
    assert provider.remove("missing") is None
    assert provider.truncate() is None
    provider.save.assert_not_called()


def test_serialize_deserialize_dump(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    source = make_store()
    data = provider.serialize(source)
    target = RemoteStoreItem()
    provider.deserialize(data, target)
    assert target.id == source.id
    assert target.status == source.status
    assert target.file_ids == ["file-1", "file-2"]
    assert json.loads(provider.dump(source)) == data
