#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.index import IndexItem


def test_index_item_defaults_and_round_trip():
    item = IndexItem()
    assert item.id is None
    assert item.name is None
    assert item.store is None
    assert item.items == {}

    payload = {"id": "idx-1", "name": "Docs", "store": "main", "items": {"a": 1}}
    item.deserialize(payload)
    assert item.serialize() == payload
    assert json.loads(item.dump()) == payload
    assert str(item) == item.dump()


def test_index_item_deserialize_is_partial():
    item = IndexItem()
    item.id = "keep"
    item.name = "old"
    item.deserialize({"name": "new"})
    assert item.id == "keep"
    assert item.name == "new"


def test_index_item_dump_returns_empty_string_on_serialization_error():
    with patch("pygpt_net.item.index.json.dumps", side_effect=TypeError):
        assert IndexItem().dump() == ""
