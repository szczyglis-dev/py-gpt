import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packaging.version import Version

from pygpt_net.item.notepad import NotepadItem
from pygpt_net.provider.core.notepad.json_file import JsonFileProvider


def make_window(path):
    return SimpleNamespace(core=SimpleNamespace(
        config=SimpleNamespace(path=str(path), append_meta=MagicMock(return_value={"v": 1})),
        debug=SimpleNamespace(log=MagicMock()),
    ))


def make_item(item_id=1):
    item = NotepadItem()
    item.id = item_id
    item.title = "Title"
    item.content = "Body"
    item.created = 1_700_000_000
    item.updated = 1_700_000_100
    return item


def test_create_id_and_existing_id(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    with patch("pygpt_net.provider.core.notepad.json_file.uuid.uuid4", return_value="fixed"):
        item = NotepadItem(); item.id = None
        assert provider.create(item) == "fixed"
    item.id = "existing"
    provider.create_id = MagicMock()
    assert provider.create(item) == "existing"
    provider.create_id.assert_not_called()


def test_save_all_and_load_all_round_trip_uses_timestamps(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    provider.save_all({1: make_item(1)})
    raw = json.loads((tmp_path / "notepad.json").read_text(encoding="utf-8"))
    assert raw["items"]["1"]["created_at"] == 1_700_000_000
    loaded = provider.load_all()
    assert loaded[1].created == 1_700_000_000
    assert loaded[1].updated == 1_700_000_100


def test_load_all_legacy_migration_is_timezone_independent(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    (tmp_path / "notepad.json").write_text(json.dumps({"content": {"2": "legacy"}}), encoding="utf-8")
    provider.save_all = MagicMock()
    legacy_item = SimpleNamespace
    fixed_now = MagicMock()
    fixed_now.strftime.return_value = "2026-09-06T20:00:00"
    with patch("pygpt_net.provider.core.notepad.json_file.NotepadItem", side_effect=lambda: legacy_item()), \
         patch("pygpt_net.provider.core.notepad.json_file.datetime.datetime") as dt:
        dt.now.return_value = fixed_now
        loaded = provider.load_all()
    assert loaded[2].title == "Notepad 2"
    assert loaded[2].content == "legacy"
    assert loaded[2].created_at == "2026-09-06T20:00:00"
    provider.save_all.assert_called_once()


def test_load_all_invalid_data_logs_and_returns_empty(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    (tmp_path / "notepad.json").write_text("{bad", encoding="utf-8")
    assert provider.load_all() == {}
    window.core.debug.log.assert_called_once()


def test_load_returns_matching_item_and_none_for_missing(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    payload = {"items": [provider.serialize(make_item(7)), provider.serialize(make_item(8))]}
    (tmp_path / "notepad.json").write_text(json.dumps(payload), encoding="utf-8")
    assert provider.load(8).id == 8
    assert provider.load(99) is None


def test_load_logs_invalid_json(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    (tmp_path / "notepad.json").write_text("[", encoding="utf-8")
    assert provider.load(1) is None
    window.core.debug.log.assert_called_once()


def test_save_updates_only_current_item_via_save_all(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    old = make_item(1)
    new = make_item(2)
    provider.load_all = MagicMock(return_value={1: old})
    provider.save_all = MagicMock()
    provider.save(new)
    provider.save_all.assert_called_once_with({1: old, 2: new})


def test_save_and_save_all_log_errors(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    provider.load_all = MagicMock(side_effect=RuntimeError("load"))
    provider.save(make_item())
    with patch("builtins.open", side_effect=OSError("write")):
        provider.save_all({1: make_item()})
    assert window.core.debug.log.call_count == 2


def test_remove_only_saves_when_item_exists(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    item = make_item(1)
    provider.load_all = MagicMock(return_value={1: item})
    provider.save_all = MagicMock()
    provider.remove(1)
    provider.save_all.assert_called_once_with({})
    provider.save_all.reset_mock()
    provider.remove(99)
    provider.save_all.assert_not_called()


def test_truncate_writes_empty_items_and_logs_error(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    provider.truncate()
    assert json.loads((tmp_path / "notepad.json").read_text(encoding="utf-8"))["items"] == {}
    with patch("builtins.open", side_effect=OSError("write")):
        provider.truncate()
    window.core.debug.log.assert_called_once()


def test_patch_serialize_deserialize_dump(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    assert provider.patch(Version("2.8.0")) is False
    item = make_item(3)
    data = provider.serialize(item)
    assert data["created_at"] == 1_700_000_000
    target = NotepadItem()
    provider.deserialize(data, target)
    assert (target.id, target.title, target.content, target.created, target.updated) == (
        3, "Title", "Body", 1_700_000_000, 1_700_000_100,
    )
    assert json.loads(provider.dump(item)) == data
