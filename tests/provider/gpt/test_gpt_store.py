#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import os
import pytest
from unittest.mock import MagicMock
from pygpt_net.provider.api.openai.store import Store

@pytest.fixture
def fake_window():
    window = MagicMock()
    client = MagicMock()
    window.core.openai.get_client.return_value = client
    window.core.assistants.store.parse_status.return_value = "parsed_status"
    window.core.assistants.store.append_status = MagicMock()
    window.core.assistants.files.insert = MagicMock()
    return window

@pytest.fixture
def store(fake_window):
    return Store(window=fake_window)

def test_get_client(store):
    client = MagicMock()
    store.window.core.openai.get_client.return_value = client
    assert store.get_client() is client

def test_log_with_callback(store):
    callback = MagicMock()
    store.log("test message", callback)
    callback.assert_called_once_with("test message")

def test_log_print(store, capsys):
    store.log("print message", None)
    captured = capsys.readouterr().out
    assert "print message" in captured

def test_get_file(store):
    fake_client = MagicMock()
    fake_client.files.retrieve.return_value = "file_info"
    store.window.core.openai.get_client.return_value = fake_client
    result = store.get_file("file1")
    fake_client.files.retrieve.assert_called_once_with("file1")
    assert result == "file_info"

def test_upload_no_file(store, monkeypatch):
    fake_client = MagicMock()
    store.window.core.openai.get_client.return_value = fake_client
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    result = store.upload("nonexistent", "assistants")
    assert result is None
    fake_client.files.create.assert_not_called()

def test_upload_success(store, tmp_path):
    fake_client = MagicMock()
    fake_result = MagicMock()
    fake_result.id = "upload_id"
    fake_client.files.create.return_value = fake_result
    store.window.core.openai.get_client.return_value = fake_client
    file = tmp_path / "test.txt"
    file.write_text("content")
    result = store.upload(str(file), "assistants")
#    assert result == "upload_id"

def test_download(store, tmp_path):
    fake_client = MagicMock()
    content_mock = MagicMock()
    content_mock.read.return_value = b"binary_data"
    fake_client.files.content.return_value = content_mock
    store.window.core.openai.get_client.return_value = fake_client
    dest = tmp_path / "dest.bin"
    store.download("file1", str(dest))
    fake_client.files.content.assert_called_once_with("file1")
    assert dest.read_bytes() == b"binary_data"

def test_get_files_ids_all(store):
    fake_client = MagicMock()
    first_response = MagicMock()
    remote1 = MagicMock()
    remote1.id = "f1"
    remote2 = MagicMock()
    remote2.id = "f2"
    first_response.data = [remote1, remote2]
    first_response.has_more = True
    first_response.last_id = "f2"
    second_response = MagicMock()
    remote3 = MagicMock()
    remote3.id = "f3"
    second_response.data = [remote3]
    second_response.has_more = False
    fake_client.files.list.side_effect = [first_response, second_response]
    store.window.core.openai.get_client.return_value = fake_client
    result = store.get_files_ids_all([])
    assert set(result) == {"f1", "f2", "f3"}
    assert fake_client.files.list.call_count == 2

def test_get_files_ids(store):
    fake_client = MagicMock()
    remote1 = MagicMock()
    remote1.id = "f1"
    remote2 = MagicMock()
    remote2.id = "f2"
    response = MagicMock()
    response.data = [remote1, remote2]
    fake_client.files.list.return_value = response
    store.window.core.openai.get_client.return_value = fake_client
    result = store.get_files_ids()
    assert set(result) == {"f1", "f2"}

def test_remove_files(store):
    store.get_files_ids = MagicMock(return_value=["f1", "f2"])
    def fake_delete_file(file_id):
        if file_id == "f1":
            return file_id
        raise Exception("fail")
    store.delete_file = MagicMock(side_effect=fake_delete_file)
    callback = MagicMock()
    result = store.remove_files(callback)
    assert result == 1
    assert store.delete_file.call_count == 2
    assert callback.call_count == 3

def test_remove_store_files(store):
    store.get_store_files_ids = MagicMock(return_value=["f1", "f2"])
    def fake_delete_store_file(store_id, file_id):
        if file_id == "f1":
            return "ok"
        raise Exception("fail")
    store.delete_store_file = MagicMock(side_effect=fake_delete_store_file)
    callback = MagicMock()
    result = store.remove_store_files("store1", callback)
    assert result == 1
    assert store.delete_store_file.call_count == 2
    assert callback.call_count == 3

def test_import_stores(store):
    fake_client = MagicMock()
    remote = MagicMock()
    remote.id = "s1"
    remote.name = "Store 1"
    response = MagicMock()
    response.data = [remote]
    response.has_more = False
    fake_client.vector_stores.list.return_value = response
    store.window.core.openai.get_client.return_value = fake_client
    store.window.core.assistants.store.parse_status.return_value = "parsed_status"
    items = {}
    callback = MagicMock()
    result = store.import_stores(items, callback=callback)
    assert "s1" in result
    item = result["s1"]
    assert item.id == "s1"
    assert item.name == "Store 1"
    assert item.file_ids == []
    assert item.status == "parsed_status"
    store.window.core.assistants.store.append_status.assert_called_with(item, "parsed_status")
    callback.assert_called_once_with("Imported vector store: s1")

def test_create_store(store):
    fake_client = MagicMock()
    fake_vector_store = MagicMock()
    fake_vector_store.id = "vs1"
    fake_client.vector_stores.create.return_value = fake_vector_store
    store.window.core.openai.get_client.return_value = fake_client
    result = store.create_store("Test Store", expire_days=0)
    fake_client.vector_stores.create.assert_called_once_with(name="Test Store", expires_after=None)
    assert result is fake_vector_store
    fake_client.vector_stores.create.reset_mock()
    fake_vector_store2 = MagicMock()
    fake_vector_store2.id = "vs2"
    fake_client.vector_stores.create.return_value = fake_vector_store2
    result = store.create_store("Test Store Exp", expire_days=5)
    fake_client.vector_stores.create.assert_called_once_with(name="Test Store Exp", expires_after={"anchor": "last_active_at", "days": 5})
    assert result is fake_vector_store2

def test_update_store(store):
    fake_client = MagicMock()
    fake_updated_store = MagicMock()
    fake_updated_store.id = "vs1"
    fake_client.vector_stores.update.return_value = fake_updated_store
    store.window.core.openai.get_client.return_value = fake_client
    result = store.update_store("vs1", "Updated Store", expire_days=0)
    fake_client.vector_stores.update.assert_called_once_with(vector_store_id="vs1", name="Updated Store", expires_after=None)
    assert result is fake_updated_store
    fake_client.vector_stores.update.reset_mock()
    fake_updated_store2 = MagicMock()
    fake_updated_store2.id = "vs2"
    fake_client.vector_stores.update.return_value = fake_updated_store2
    result = store.update_store("vs2", "Updated Store Exp", expire_days=3)
    fake_client.vector_stores.update.assert_called_once_with(vector_store_id="vs2", name="Updated Store Exp", expires_after={"anchor": "last_active_at", "days": 3})
    assert result is fake_updated_store2

def test_get_store(store):
    fake_client = MagicMock()
    fake_vector_store = MagicMock()
    fake_vector_store.id = "vs1"
    fake_client.vector_stores.retrieve.return_value = fake_vector_store
    store.window.core.openai.get_client.return_value = fake_client
    result = store.get_store("vs1")
    fake_client.vector_stores.retrieve.assert_called_once_with(vector_store_id="vs1")
    assert result is fake_vector_store

def test_remove_store(store):
    fake_client = MagicMock()
    fake_vector_store = MagicMock()
    fake_vector_store.id = "vs1"
    fake_client.vector_stores.delete.return_value = fake_vector_store
    store.window.core.openai.get_client.return_value = fake_client
    result = store.remove_store("vs1")
    fake_client.vector_stores.delete.assert_called_once_with(vector_store_id="vs1")
    assert result is fake_vector_store

def test_get_stores_ids(store):
    fake_client = MagicMock()
    remote1 = MagicMock()
    remote1.id = "s1"
    remote2 = MagicMock()
    remote2.id = "s2"
    response = MagicMock()
    response.data = [remote1, remote2]
    response.has_more = False
    fake_client.vector_stores.list.return_value = response
    store.window.core.openai.get_client.return_value = fake_client
    result = store.get_stores_ids([])
    assert set(result) == {"s1", "s2"}

def test_get_store_files_ids(store):
    fake_client = MagicMock()
    remote1 = MagicMock()
    remote1.id = "f1"
    remote2 = MagicMock()
    remote2.id = "f2"
    response = MagicMock()
    response.data = [remote1, remote2]
    response.has_more = False
    fake_client.vector_stores.files.list.return_value = response
    store.window.core.openai.get_client.return_value = fake_client
    result = store.get_store_files_ids("s1", [])
    assert set(result) == {"f1", "f2"}

def test_remove_from_stores(store):
    store.get_stores_ids = MagicMock(return_value=["s1", "s2"])
    store.get_store_files_ids = MagicMock(side_effect=lambda store_id, items: ["f_" + store_id + "1", "f_" + store_id + "2"])
    store.delete_store_file = MagicMock(return_value="deleted")
    store.log = MagicMock()
    result = store.remove_from_stores()
    assert result == 4
    assert store.delete_store_file.call_count == 4

def test_remove_from_store(store):
    store.get_store_files_ids = MagicMock(return_value=["f1", "f2"])
    store.delete_store_file = MagicMock(return_value="deleted")
    store.log = MagicMock()
    result = store.remove_from_store("s1")
    assert result == 2
    assert store.delete_store_file.call_count == 2

def test_remove_all(store):
    store.get_stores_ids = MagicMock(return_value=["s1", "s2"])
    def fake_remove_store(store_id):
        if store_id == "s1":
            return "ok"
        raise Exception("fail")
    store.remove_store = MagicMock(side_effect=fake_remove_store)
    store.log = MagicMock()
    callback = MagicMock()
    result = store.remove_all(callback)
    assert result == 1
    assert store.remove_store.call_count == 2

def test_add_file(store):
    fake_client = MagicMock()
    fake_vector_store_file = MagicMock()
    fake_client.vector_stores.files.create.return_value = fake_vector_store_file
    store.window.core.openai.get_client.return_value = fake_client
    result = store.add_file("s1", "f1")
    fake_client.vector_stores.files.create.assert_called_once_with(vector_store_id="s1", file_id="f1")
    assert result is fake_vector_store_file

def test_delete_file(store):
    fake_client = MagicMock()
    fake_deleted = MagicMock()
    fake_deleted.id = "f1"
    fake_client.files.delete.return_value = fake_deleted
    store.window.core.openai.get_client.return_value = fake_client
    result = store.delete_file("f1")
    fake_client.files.delete.assert_called_once_with(file_id="f1")
    assert result == "f1"

def test_delete_store_file(store):
    fake_client = MagicMock()
    fake_vector_store_file = MagicMock()
    fake_client.vector_stores.files.delete.return_value = fake_vector_store_file
    store.window.core.openai.get_client.return_value = fake_client
    result = store.delete_store_file("s1", "f1")
    fake_client.vector_stores.files.delete.assert_called_once_with(vector_store_id="s1", file_id="f1")
    assert result is fake_vector_store_file

def test_import_stores_files(store):
    store.get_stores_ids = MagicMock(return_value=["s1", "s2"])
    store.import_store_files = MagicMock(side_effect=lambda store_id, items, callback=None, order="asc", limit=100, after=None: ["f1"] if store_id=="s1" else [])
    store.log = MagicMock()
    result = store.import_stores_files()
    assert result == 1

def test_import_store_files(store):
    fake_client = MagicMock()
    remote = MagicMock()
    remote.id = "f1"
    response = MagicMock()
    response.data = [remote]
    response.has_more = False
    fake_client.vector_stores.files.list.return_value = response
    store.window.core.openai.get_client.return_value = fake_client
    store.get_file = MagicMock(return_value="file_data")
    store.window.core.assistants.files.insert = MagicMock()
    store.log = MagicMock()
    items = []
    callback = MagicMock()
    result = store.import_store_files("s1", items, callback=callback)
    assert result == ["f1"]
    fake_client.vector_stores.files.list.assert_called_once()
    store.get_file.assert_called_once_with("f1")
    store.window.core.assistants.files.insert.assert_called_once_with("s1", "file_data")