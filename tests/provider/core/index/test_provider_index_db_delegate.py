from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from packaging.version import Version

from pygpt_net.provider.core.index.db_sqlite.provider import DbSqliteProvider


def make_window():
    return SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())))


def provider():
    p = DbSqliteProvider(make_window())
    p.storage = MagicMock()
    p.patcher = MagicMock()
    return p


def test_attach_and_patch_delegate():
    p = provider(); window = make_window()
    p.attach(window)
    assert p.window is window
    p.storage.attach.assert_called_once_with(window)
    version = Version("2.8.0"); p.patcher.execute.return_value = True
    assert p.patch(version) is True
    p.patcher.execute.assert_called_once_with(version)


@pytest.mark.parametrize("method,args,target,kwargs", [
    ("load", ("store",), "get_items", {}),
    ("get_index_ids", ("store",), "get_index_ids", {}),
    ("get_file_status", ("store", "file"), "get_file_status", {}),
    ("get_file_record", ("store", "idx", "file"), "get_file_record", {}),
    ("get_files_by_index", ("store", "idx"), "get_files_by_index", {}),
    ("append_file", ("store", "idx", {"x": 1}), "insert_file", {}),
    ("append_ctx_meta", ("store", "idx", 3, "doc"), "insert_ctx_meta", {}),
    ("append_external", ("store", "idx", {"x": 1}), "insert_external", {}),
    ("get_ctx_meta_index_data", (), "get_ctx_meta_index_data", {"meta_id": 3, "group_id": 4}),
    ("get_ctx_records", (), "get_ctx_records", {"meta_id": 3, "group_id": 4}),
    ("remove_ctx_record", (8,), "remove_ctx_record", {}),
    ("get_index_stores", ("idx",), "get_index_stores", {}),
    ("is_meta_indexed", ("store", "idx", 3), "is_meta_indexed", {}),
    ("get_ctx_updated_ts", ("store", "idx", 3), "get_ctx_updated_ts", {}),
    ("is_file_indexed", ("store", "idx", "file"), "is_file_indexed", {}),
    ("is_external_indexed", ("store", "idx", "url", "web"), "is_external_indexed", {}),
    ("get_meta_doc_id", ("store", "idx", 3), "get_meta_doc_id", {}),
    ("get_file_doc_id", ("store", "idx", "file"), "get_file_doc_id", {}),
    ("get_external_doc_id", ("store", "idx", "url", "web"), "get_external_doc_id", {}),
    ("update_file", (1, "doc", 1_700_000_000), "update_file", {}),
    ("update_ctx_meta", ("store", "idx", 3, "doc"), "update_ctx_meta", {}),
    ("update_external", ("url", "web", "doc", 1_700_000_000), "update_external", {}),
    ("remove_file", ("store", "idx", "doc"), "remove_file", {}),
    ("remove_ctx_meta", ("store", "idx", 3), "remove_ctx_meta", {}),
    ("remove_external", ("store", "idx", "doc"), "remove_external", {}),
    ("truncate", ("store", "idx"), "truncate_all", {}),
    ("truncate_all", ("store", "idx"), "truncate_all", {}),
    ("truncate_files", ("store", "idx"), "truncate_files", {}),
    ("truncate_ctx", ("store", "idx"), "truncate_ctx", {}),
    ("truncate_external", ("store", "idx"), "truncate_external", {}),
    ("get_project", (4,), "get_project", {}),
    ("get_projects", (), "get_projects", {}),
    ("upsert_project", (4, "idx", 10, 20, 1_700_000_000), "upsert_project", {}),
    ("remove_project", (4,), "remove_project", {}),
    ("truncate_projects", (), "truncate_projects", {}),
    ("get_counters", ("file",), "get_counters", {}),
])
def test_storage_delegates(method, args, target, kwargs):
    p = provider(); expected = object()
    getattr(p.storage, target).return_value = expected
    result = getattr(p, method)(*args, **kwargs)
    getattr(p.storage, target).assert_called_once_with(*args, **kwargs)
    if method not in {"remove_file", "remove_ctx_meta", "remove_external"}:
        assert result is expected
