#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.agent import AgentItem


def test_agent_item_defaults_and_reset():
    item = AgentItem()
    assert item.id is None
    assert item.name is None
    assert item.layout == {}
    assert item.schema == []

    item.id = "a1"
    item.name = "Agent"
    item.layout = {"x": 1}
    item.schema = [{"id": 1}]
    item.reset()

    assert item.id is None
    assert item.name is None
    assert item.layout == {}
    # Preserve the current reset contract.
    assert item.schema == {}


def test_agent_item_to_dict_dump_and_str():
    item = AgentItem()
    item.id = "a1"
    item.name = "Agent"
    item.layout = {"nodes": [1]}
    item.schema = [{"name": "worker"}]

    expected = {
        "id": "a1",
        "name": "Agent",
        "layout": {"nodes": [1]},
        "schema": [{"name": "worker"}],
    }
    assert item.to_dict() == expected
    assert json.loads(item.dump()) == expected
    assert str(item) == item.dump()


def test_agent_item_dump_returns_empty_string_on_serialization_error():
    item = AgentItem()
    with patch("pygpt_net.item.agent.json.dumps", side_effect=TypeError("bad data")):
        assert item.dump() == ""
