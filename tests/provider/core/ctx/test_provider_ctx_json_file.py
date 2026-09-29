import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packaging.version import Version

from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.provider.core.ctx.json_file import JsonFileProvider


def make_window(path):
    (path / "context").mkdir(exist_ok=True)
    return SimpleNamespace(core=SimpleNamespace(
        config=SimpleNamespace(path=str(path), append_meta=MagicMock(return_value={"v": 1})),
        debug=SimpleNamespace(log=MagicMock()),
    ))


def make_meta(meta_id="ctx-1"):
    meta = CtxMeta()
    meta.id = meta_id
    meta.name = "Context"
    meta.mode = "chat"
    meta.last_mode = "chat"
    meta.thread = "thread"
    meta.assistant = "assistant"
    meta.preset = "preset"
    meta.run = "run"
    meta.status = "ready"
    meta.initialized = True
    return meta


def make_item():
    item = CtxItem()
    item.input = "hello"
    item.output = "world"
    item.mode = "chat"
    item.thread = "thread"
    item.msg_id = "m1"
    item.run_id = "r1"
    item.input_name = "User"
    item.output_name = "AI"
    item.input_tokens = 2
    item.output_tokens = 3
    item.total_tokens = 5
    item.input_timestamp = 1_700_000_000
    item.output_timestamp = 1_700_000_001
    return item


def test_install_and_create_id(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    assert provider.install() is None
    with patch("pygpt_net.provider.core.ctx.json_file.datetime.datetime") as dt:
        dt.now.return_value.strftime.return_value = "20260906200000.123456"
        assert provider.create_id() == "20260906200000.123456"


def test_create_assigns_id_only_if_missing(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    provider.create_id = MagicMock(return_value="new")
    meta = make_meta("")
    assert provider.create(meta) == "new"
    meta.id = "existing"
    provider.create_id.reset_mock()
    assert provider.create(meta) == "existing"
    provider.create_id.assert_not_called()


def test_save_get_meta_and_load_round_trip(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    meta = make_meta()
    item = make_item()
    provider.save(meta.id, meta, [item])
    metas = provider.get_meta(search_string="ignored", order_by="name", limit=1, offset=2)
    assert metas[meta.id].name == "Context"
    loaded = provider.load(meta.id)
    assert len(loaded) == 1
    assert loaded[0].input_timestamp == 1_700_000_000
    assert loaded[0].output == "world"


def test_get_meta_and_load_handle_missing_empty_invalid(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    assert provider.get_meta() == {}
    assert provider.load("missing") == []
    (tmp_path / "context.json").write_text("null", encoding="utf-8")
    assert provider.get_meta() == {}
    (tmp_path / "context.json").write_text("{bad", encoding="utf-8")
    assert provider.get_meta() == {}
    (tmp_path / "context" / "x.json").write_text("[", encoding="utf-8")
    assert provider.load("x") == []
    assert window.core.debug.log.call_count == 2


def test_append_is_explicitly_deferred(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    assert provider.append(make_meta(), make_item()) is False


def test_save_logs_write_error(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    with patch("builtins.open", side_effect=OSError("write")):
        provider.save("ctx", make_meta("ctx"), [make_item()])
    window.core.debug.log.assert_called_once()


def test_remove_updates_index_and_removes_item_file(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    a, b = make_meta("a"), make_meta("b")
    provider.save("a", a, [make_item()])
    provider.save("b", b, [make_item()])
    provider.remove("a")
    assert "a" not in provider.get_meta()
    assert "b" in provider.get_meta()
    assert not (tmp_path / "context" / "a.json").exists()


def test_remove_logs_os_remove_error(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    provider.get_meta = MagicMock(return_value={})
    path = tmp_path / "context" / "x.json"
    path.write_text("[]", encoding="utf-8")
    with patch("pygpt_net.provider.core.ctx.json_file.os.remove", side_effect=OSError("locked")):
        provider.remove("x")
    window.core.debug.log.assert_called_once()


def test_truncate_removes_context_files_and_writes_empty_index(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    for meta_id in ("a", "b"):
        provider.save(meta_id, make_meta(meta_id), [make_item()])
    provider.truncate()
    assert not (tmp_path / "context" / "a.json").exists()
    assert not (tmp_path / "context" / "b.json").exists()
    assert json.loads((tmp_path / "context.json").read_text(encoding="utf-8"))["items"] == {}


def test_truncate_logs_delete_and_write_errors(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    provider.get_meta = MagicMock(return_value={"a": make_meta("a")})
    (tmp_path / "context" / "a.json").write_text("[]", encoding="utf-8")
    real_open = open
    def failing_open(path, *args, **kwargs):
        if str(path).endswith("context.json"):
            raise OSError("write")
        return real_open(path, *args, **kwargs)
    with patch("pygpt_net.provider.core.ctx.json_file.os.remove", side_effect=OSError("remove")), \
         patch("builtins.open", side_effect=failing_open):
        provider.truncate()
    assert window.core.debug.log.call_count == 2


def test_patch_serialization_parsers_and_dump(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    assert provider.patch(Version("2.8.0")) is False
    meta = make_meta()
    item = make_item()
    meta_data = provider.serialize_meta(meta)
    item_data = provider.serialize_item(item)
    meta_target = CtxMeta()
    item_target = CtxItem()
    assert provider.deserialize_meta(meta_data, meta_target) is meta_target
    provider.deserialize_item(item_data, item_target)
    assert meta_target.id == "ctx-1"
    assert item_target.total_tokens == 5
    assert provider.parse_meta({"k": meta_data})["ctx-1"].name == "Context"
    assert provider.parse_data([item_data])[0].msg_id == "m1"
    assert json.loads(provider.dump(item)) == item_data
