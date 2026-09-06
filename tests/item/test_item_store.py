#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.store import RemoteFileItem, RemoteStoreItem


def test_remote_store_defaults_use_mocked_timestamp():
    with patch("pygpt_net.item.store.time.time", return_value=1_700_000_000):
        item = RemoteStoreItem()

    assert item.id is None
    assert item.record_id is None
    assert item.status == {}
    assert item.expire_days == 0
    assert item.num_files == 0
    assert item.created == 1_700_000_000
    assert item.updated == 1_700_000_000
    assert item.last_active == 1_700_000_000
    assert item.last_sync == 1_700_000_000


def test_remote_store_reset_preserves_created_updated_and_refreshes_activity():
    with patch("pygpt_net.item.store.time.time", return_value=100):
        item = RemoteStoreItem()
    item.id = "store"
    item.created = 11
    item.updated = 22
    item.num_files = 7

    with patch("pygpt_net.item.store.time.time", return_value=200):
        item.reset()

    assert item.id is None
    assert item.num_files == 0
    assert item.created == 11
    assert item.updated == 22
    assert item.last_active == 200
    assert item.last_sync == 200


def test_remote_store_to_from_dict_file_count_and_dump():
    with patch("pygpt_net.item.store.time.time", return_value=1):
        item = RemoteStoreItem()
    item.from_dict({
        "id": "s1",
        "name": "Store",
        "provider": "openai",
        "uuid": "u1",
        "expire_days": 30,
        "status": {"file_counts": {"completed": "4"}},
    })
    item.description = "desc"
    item.last_status = "ok"
    item.usage_bytes = 123
    item.num_files = 9
    item.is_thread = True

    assert item.get_file_count() == 4
    item.status = {"file_counts": {"completed": None}}
    assert item.get_file_count() == 0
    item.status = {}
    assert item.get_file_count() == 9

    data = item.to_dict()
    assert data["id"] == "s1"
    assert data["description"] == "desc"
    assert json.loads(item.dump()) == data
    assert str(item) == item.dump()


def test_remote_store_dump_returns_empty_string_on_serialization_error():
    with patch("pygpt_net.item.store.time.time", return_value=1), \
            patch("pygpt_net.item.store.json.dumps", side_effect=TypeError):
        assert RemoteStoreItem().dump() == ""


def test_remote_file_defaults_reset_round_trip_and_dump():
    item = RemoteFileItem()
    assert item.id is None
    assert item.size == 0
    assert item.created == 0
    assert item.updated == 0

    payload = {
        "id": "row-1",
        "name": "a.txt",
        "provider": "openai",
        "path": "/tmp/a.txt",
        "file_id": "file-1",
        "store_id": "store-1",
        "thread_id": "thread-1",
        "uuid": "uuid-1",
        "size": 123,
        "created": 10,
        "updated": 20,
    }
    item.from_dict(payload)
    assert item.to_dict() == payload
    assert json.loads(item.dump()) == payload
    assert str(item) == item.dump()

    item.reset()
    assert item.to_dict() == {
        "id": None,
        "name": None,
        "provider": None,
        "path": None,
        "file_id": None,
        "store_id": None,
        "thread_id": None,
        "uuid": None,
        "size": 0,
        "created": 0,
        "updated": 0,
    }


def test_remote_file_from_dict_defaults_and_dump_error():
    item = RemoteFileItem()
    item.from_dict({"id": "x"})
    assert item.id == "x"
    assert item.size == 0
    assert item.created == 0

    with patch("pygpt_net.item.store.json.dumps", side_effect=TypeError):
        assert item.dump() == ""
