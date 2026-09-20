import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packaging.version import Version

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.core.index.json_file import JsonFileProvider


def make_window(path):
    return SimpleNamespace(core=SimpleNamespace(
        config=SimpleNamespace(path=str(path), append_meta=MagicMock(return_value={"version": "test"})),
        debug=SimpleNamespace(log=MagicMock()),
    ))


def make_index(idx="idx", store="SimpleVectorStore", name="Index"):
    item = IndexItem()
    item.id = idx
    item.name = name
    item.store = store
    item.items = {"doc.txt": {"id": "doc-1"}}
    return item


def test_create_id_and_create_preserve_existing_id(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    with patch("pygpt_net.provider.core.index.json_file.uuid.uuid4", return_value="uuid-1"):
        fresh = IndexItem()
        assert provider.create(fresh) == "uuid-1"
        assert fresh.id == "uuid-1"
    existing = make_index("existing")
    provider.create_id = MagicMock(return_value="unused")
    assert provider.create(existing) == "existing"
    provider.create_id.assert_not_called()


def test_save_and_load_round_trip_adds_item_name(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    item = make_index()
    provider.save({"SimpleVectorStore": {item.id: item}})

    raw = json.loads((tmp_path / "indexes.json").read_text(encoding="utf-8"))
    assert raw["__meta__"] == {"version": "test"}
    loaded = provider.load()
    assert loaded["SimpleVectorStore"]["idx"].id == "idx"
    assert loaded["SimpleVectorStore"]["idx"].items["doc.txt"]["name"] == "doc.txt"


def test_load_migrates_legacy_shape_and_persists_it(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    legacy = {
        "items": {
            "old-index": {"id": "old-index", "name": "Old", "store": "", "items": {}}
        }
    }
    (tmp_path / "indexes.json").write_text(json.dumps(legacy), encoding="utf-8")
    provider.save = MagicMock()

    loaded = provider.load()

    assert loaded["SimpleVectorStore"]["old-index"].store == "SimpleVectorStore"
    provider.save.assert_called_once_with(loaded)


def test_load_handles_empty_missing_and_invalid_files(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    assert provider.load() == {}

    (tmp_path / "indexes.json").write_text("null", encoding="utf-8")
    assert provider.load() == {}
    (tmp_path / "indexes.json").write_text("{}", encoding="utf-8")
    assert provider.load() == {}
    (tmp_path / "indexes.json").write_text("{broken", encoding="utf-8")
    assert provider.load() == {}
    window.core.debug.log.assert_called()


def test_save_and_truncate_log_io_errors(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    with patch("builtins.open", side_effect=OSError("write failed")):
        provider.save({"SimpleVectorStore": {"idx": make_index()}})
        provider.truncate("store", "idx")
    assert window.core.debug.log.call_count == 2


def test_truncate_writes_empty_payload(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    provider.truncate("ignored-store", "ignored-index")
    data = json.loads((tmp_path / "indexes.json").read_text(encoding="utf-8"))
    assert data == {"__meta__": {"version": "test"}, "items": {}}


def test_install_creates_default_index_only_when_missing(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    provider.save = MagicMock()
    assert provider.install() is True
    payload = provider.save.call_args.args[0]
    assert payload["SimpleVectorStore"]["base"].name == "base"

    (tmp_path / "indexes.json").write_text("{}", encoding="utf-8")
    provider.save.reset_mock()
    assert provider.install() is True
    provider.save.assert_not_called()


def test_patch_delegates_and_remove_is_noop(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    provider.patcher.execute = MagicMock(return_value=True)
    version = Version("2.8.0")
    assert provider.patch(version) is True
    provider.patcher.execute.assert_called_once_with(version)
    assert provider.remove("unused") is None


def test_serialize_deserialize_and_dump_are_stable(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    item = make_index()
    serialized = provider.serialize(item)
    assert serialized == {
        "id": "idx", "name": "Index", "store": "SimpleVectorStore",
        "items": {"doc.txt": {"id": "doc-1"}},
    }

    target = IndexItem()
    provider.deserialize({"id": "x", "items": {"a.pdf": {}}}, target)
    assert target.id == "x"
    assert target.items["a.pdf"]["name"] == "a.pdf"
    assert json.loads(provider.dump(item)) == serialized
