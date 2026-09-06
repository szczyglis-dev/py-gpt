#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.preset import PresetItem


def test_preset_item_integrity():
    item = PresetItem()
    assert item.name == "*"
    assert item.ai_name == ""
    assert item.user_name == ""
    assert item.prompt == ""
    assert item.chat is False
    assert item.completion is False
    assert item.img is False
    assert item.vision is False
    assert item.langchain is False
    assert item.assistant is False
    assert item.temperature == 1.0
    assert item.filename is None
    assert item.version is None
    assert item.agent_v2_allow_local_tools is True
    assert item.agent_v2_allow_remote_tools is True
    assert item.enabled is True
    assert item.tools == {"function": []}


def test_preset_get_id_and_to_dict():
    item = PresetItem()
    item.filename = "coder.json"
    item.name = "Coder"
    item.agent_v2 = True
    item.remote_tools = ["web"]
    item.extra = {"x": 1}
    item.tools["function"] = [{"name": "run"}]

    assert item.get_id() == "coder.json"
    data = item.to_dict()
    assert data["filename"] == "coder.json"
    assert data["name"] == "Coder"
    assert data["agent_v2"] is True
    assert data["remote_tools"] == ["web"]
    assert data["tool.function"] == [{"name": "run"}]
    assert data["uuid"] == "None"


def test_preset_from_dict_loads_fields_and_normalizes_uuid():
    raw_uuid = "12345678-1234-5678-1234-567812345678"
    item = PresetItem().from_dict({
        "agent": True,
        "agent_llama": True,
        "agent_openai": True,
        "agent_v2": 1,
        "agent_v2_allow_local_tools": 0,
        "agent_v2_allow_remote_tools": 1,
        "agent_provider": "x",
        "agent_provider_openai": "y",
        "ai_avatar": "avatar",
        "ai_name": "AI",
        "ai_personalize": True,
        "assistant": True,
        "assistant_id": "asst",
        "audio": True,
        "chat": True,
        "completion": True,
        "computer": True,
        "description": "desc",
        "enabled": False,
        "expert": True,
        "experts": ["a"],
        "extra": {"k": "v"},
        "filename": "f.json",
        "img": True,
        "idx": 4,
        "langchain": True,
        "llama_index": True,
        "model": "m",
        "name": "n",
        "prompt": "p",
        "remote_tools": ["web"],
        "research": True,
        "temperature": 0.4,
        "tool.function": [{"name": "fn"}],
        "user_name": "User",
        "uuid": raw_uuid,
        "vision": True,
    })

    assert item is not None
    assert item.agent is True
    assert item.agent_v2 is True
    assert item.agent_v2_allow_local_tools is False
    assert item.agent_v2_allow_remote_tools is True
    assert item.experts == ["a"]
    assert item.remote_tools == ["web"]
    assert item.tools["function"] == [{"name": "fn"}]
    assert item.uuid == raw_uuid
    assert item.vision is True


def test_preset_from_dict_is_partial():
    item = PresetItem()
    item.name = "keep"
    item.temperature = 0.9
    returned = item.from_dict({"prompt": "new"})
    assert returned is item
    assert item.name == "keep"
    assert item.temperature == 0.9
    assert item.prompt == "new"


def test_preset_reset_modes():
    item = PresetItem()
    for name in (
        "agent", "agent_llama", "agent_openai", "agent_v2", "audio",
        "assistant", "chat", "completion", "computer", "expert",
        "langchain", "llama_index", "research", "vision",
    ):
        setattr(item, name, True)

    item.reset_modes()
    assert all(getattr(item, name) is False for name in (
        "agent", "agent_llama", "agent_openai", "agent_v2", "audio",
        "assistant", "chat", "completion", "computer", "expert",
        "langchain", "llama_index", "research", "vision",
    ))


def test_preset_function_management():
    item = PresetItem()
    assert item.has_functions() is False
    item.add_function("f", '{"x":1}', "desc")
    assert item.has_functions() is True
    assert item.get_functions() == [{"name": "f", "params": '{"x":1}', "desc": "desc"}]


def test_preset_dump_str_and_serialization_error():
    item = PresetItem()
    assert json.loads(item.dump())["name"] == "*"
    assert str(item) == item.dump()

    with patch("pygpt_net.item.preset.json.dumps", side_effect=TypeError):
        assert item.dump() == ""
