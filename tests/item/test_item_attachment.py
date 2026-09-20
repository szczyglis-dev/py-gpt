#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.attachment import AttachmentItem


def test_attachment_item_integrity():
    item = AttachmentItem()
    assert item.name is None
    assert item.id is None
    assert item.uuid is None
    assert item.path is None
    assert item.remote is None
    assert item.vector_store_ids == []
    assert item.meta_id is None
    assert item.ctx is False
    assert item.consumed is False
    assert item.size == 0
    assert item.send is False
    assert item.type == AttachmentItem.TYPE_FILE
    assert item.extra == {}


def test_attachment_serialize_and_deserialize_round_trip():
    item = AttachmentItem(
        id="a1",
        uuid="u1",
        name="file.txt",
        path="/tmp/file.txt",
        remote="remote-1",
        vector_store_ids=["vs1"],
        meta_id=7,
        ctx=True,
        consumed=True,
        size=42,
        send=True,
        type=AttachmentItem.TYPE_URL,
        extra={"k": "v"},
    )
    data = item.serialize()
    assert data == {
        "id": "a1",
        "uuid": "u1",
        "name": "file.txt",
        "path": "/tmp/file.txt",
        "size": 42,
        "remote": "remote-1",
        "ctx": True,
        "vector_store_ids": ["vs1"],
        "type": "url",
        "extra": {"k": "v"},
        "meta_id": 7,
        "send": True,
    }

    restored = AttachmentItem()
    restored.deserialize(data)
    assert restored.serialize() == data
    # Runtime-only field is intentionally not serialized.
    assert restored.consumed is False


def test_attachment_deserialize_supports_legacy_remote_id_and_partial_data():
    item = AttachmentItem(id="keep", name="old")
    item.deserialize({"remote_id": "legacy", "name": "new"})
    assert item.id == "keep"
    assert item.remote == "legacy"
    assert item.name == "new"

    item.deserialize({"remote": "new-remote", "remote_id": "ignored"})
    assert item.remote == "new-remote"


def test_attachment_dump_str_and_serialization_error():
    item = AttachmentItem(id="a1", name="x")
    assert json.loads(item.dump()) == item.serialize()
    assert str(item) == item.dump()

    with patch("pygpt_net.item.attachment.json.dumps", side_effect=TypeError):
        assert item.dump() == ""
