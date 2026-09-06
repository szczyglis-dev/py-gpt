#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.prompt import PromptItem


def test_prompt_item_defaults_round_trip_and_partial_deserialize():
    item = PromptItem()
    assert item.id is None
    assert item.name is None
    assert item.content is None
    assert item.serialize() == {"id": "None", "name": None, "content": None}

    item.deserialize({"id": "p1", "name": "Coder", "content": "Write code"})
    assert item.id == "p1"
    assert item.name == "Coder"
    assert item.content == "Write code"
    assert json.loads(item.dump()) == item.serialize()
    assert str(item) == item.dump()

    item.deserialize({"content": "Updated"})
    assert item.id == "p1"
    assert item.name == "Coder"
    assert item.content == "Updated"


def test_prompt_item_dump_returns_empty_string_on_serialization_error():
    with patch("pygpt_net.item.prompt.json.dumps", side_effect=TypeError):
        assert PromptItem().dump() == ""
