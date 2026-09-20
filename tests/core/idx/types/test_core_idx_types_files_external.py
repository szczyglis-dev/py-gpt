import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.idx.types.external as external_mod
import pygpt_net.core.idx.types.files as files_mod
from pygpt_net.core.idx.types.external import External
from pygpt_net.core.idx.types.files import Files


FIXED_TS = 1_735_689_600


class FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        # Use an aware UTC value even though production calls now() without a TZ.
        # The tested code only consumes .timestamp(), so this keeps the epoch
        # deterministic without consulting the host timezone.
        return cls.fromtimestamp(FIXED_TS, tz=tz or datetime.timezone.utc)


def test_files_append_uses_deterministic_epoch_timestamp(monkeypatch):
    monkeypatch.setattr(files_mod.datetime, "datetime", FixedDateTime)
    provider = MagicMock()
    provider.append_file.return_value = 5
    files = Files(provider=provider)
    assert files.append("store", "idx", "file/a.txt", "/data/file/a.txt", "doc") == 5
    data = provider.append_file.call_args.kwargs["data"]
    assert data == {
        "name": "file/a.txt",
        "path": "/data/file/a.txt",
        "indexed_ts": float(FIXED_TS),
        "id": "doc",
    }


def test_files_get_id_normalizes_path_relative_to_data_directory(tmp_path):
    data_dir = tmp_path / "data"
    nested = data_dir / "a" / "b.txt"
    data_dir.mkdir()
    window = SimpleNamespace(core=SimpleNamespace(config=SimpleNamespace(get_user_dir=MagicMock(return_value=str(data_dir))), filesystem=SimpleNamespace(get_data_dir=MagicMock(return_value=str(data_dir)))))
    files = Files(window=window, provider=MagicMock())
    assert files.get_id(str(nested)) == "a/b.txt"


def test_files_delegates_lookup_update_remove_and_truncate():
    provider = MagicMock()
    provider.get_file_doc_id.return_value = "doc"
    provider.is_file_indexed.return_value = True
    provider.get_file_status.return_value = [("idx", 1)]
    provider.get_file_record.return_value = {"id": 2}
    provider.update_file.return_value = True
    files = Files(provider=provider)

    assert files.get_doc_id("s", "i", "f") == "doc"
    assert files.exists("s", "i", "f") is True
    assert files.get_status("s", "f") == [("idx", 1)]
    assert files.get_record("s", "i", "f") == {"id": 2}
    assert files.update(2, "doc2", FIXED_TS) is True
    files.remove("s", "i", "doc2")
    files.truncate("s", "i")

    provider.get_file_doc_id.assert_called_once_with(store_id="s", idx="i", file_id="f")
    provider.is_file_indexed.assert_called_once_with(store_id="s", idx="i", file_id="f")
    provider.get_file_status.assert_called_once_with("s", "f")
    provider.get_file_record.assert_called_once_with("s", "i", "f")
    provider.update_file.assert_called_once_with(id=2, doc_id="doc2", ts=FIXED_TS)
    provider.remove_file.assert_called_once_with(store_id="s", idx="i", doc_id="doc2")
    provider.truncate_files.assert_called_once_with(store_id="s", idx="i")


def test_external_append_uses_deterministic_epoch_timestamp(monkeypatch):
    monkeypatch.setattr(external_mod.datetime, "datetime", FixedDateTime)
    provider = MagicMock()
    provider.append_external.return_value = 8
    ext = External(provider=provider)
    assert ext.append("store", "idx", "https://example.test", "url", "doc") == 8
    assert provider.append_external.call_args.kwargs["data"] == {
        "content": "https://example.test",
        "type": "url",
        "indexed_ts": float(FIXED_TS),
        "id": "doc",
    }


def test_external_delegates_crud_operations():
    provider = MagicMock()
    provider.get_external_doc_id.return_value = "doc"
    provider.is_external_indexed.return_value = True
    provider.update_external.return_value = True
    ext = External(provider=provider)

    assert ext.get_doc_id("s", "i", "content", "url") == "doc"
    assert ext.exists("s", "i", "content", "url") is True
    assert ext.update("content", "url", "doc2", FIXED_TS) is True
    ext.remove("s", "i", "doc2")
    ext.truncate("s", "i")

    provider.get_external_doc_id.assert_called_once_with(store_id="s", idx="i", content="content", type="url")
    provider.is_external_indexed.assert_called_once_with(store_id="s", idx="i", content="content", type="url")
    provider.update_external.assert_called_once_with(content="content", type="url", doc_id="doc2", ts=FIXED_TS)
    provider.remove_external.assert_called_once_with(store_id="s", idx="i", doc_id="doc2")
    provider.truncate_external.assert_called_once_with(store_id="s", idx="i")


def test_external_set_indexed_appends_or_updates_using_epoch_timestamp(monkeypatch):
    monkeypatch.setattr(external_mod.time, "time", lambda: FIXED_TS)
    window = SimpleNamespace(core=SimpleNamespace(idx=SimpleNamespace(get_current_store=MagicMock(return_value="store"))))
    ext = External(window=window, provider=MagicMock())
    ext.exists = MagicMock(side_effect=[False, True])
    ext.append = MagicMock()
    ext.update = MagicMock()

    assert ext.set_indexed("c1", "url", "idx", "doc1") is True
    ext.append.assert_called_once_with(store_id="store", idx="idx", content="c1", type="url", doc_id="doc1")
    ext.update.assert_not_called()

    assert ext.set_indexed("c2", "url", "idx", "doc2") is True
    ext.update.assert_called_once_with(content="c2", type="url", doc_id="doc2", ts=FIXED_TS)
