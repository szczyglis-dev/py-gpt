#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.builder_layout import BuilderLayoutItem


def test_builder_layout_defaults_reset_and_serialization():
    item = BuilderLayoutItem()
    assert (item.id, item.name, item.data) == (None, None, None)

    item.id = "layout-1"
    item.name = "Main"
    item.data = {"nodes": [{"id": 1}]}
    expected = {"id": "layout-1", "name": "Main", "data": item.data}

    assert item.to_dict() == expected
    assert json.loads(item.dump()) == expected
    assert str(item) == item.dump()

    item.reset()
    assert (item.id, item.name, item.data) == (None, None, None)


def test_builder_layout_dump_returns_empty_string_on_serialization_error():
    with patch("pygpt_net.item.builder_layout.json.dumps", side_effect=TypeError):
        assert BuilderLayoutItem().dump() == ""
