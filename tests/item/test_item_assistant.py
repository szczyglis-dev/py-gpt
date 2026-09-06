#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.attachment import AttachmentItem


def test_assistant_item_integrity():
    item = AssistantItem()
    assert item.id is None
    assert item.name is None
    assert item.description is None
    assert item.instructions is None
    assert item.model is None
    assert item.meta == {}
    assert item.files == {}
    assert item.attachments == {}
    assert item.vector_store == ""
    assert item.tools == {
        "code_interpreter": False,
        "file_search": False,
        "function": [],
    }


def test_assistant_reset_and_to_dict():
    item = AssistantItem()
    item.id = "a1"
    item.name = "Assistant"
    item.description = "desc"
    item.instructions = "help"
    item.model = "gpt-test"
    item.meta = {"x": 1}
    item.files = {"f": {"id": "f"}}
    item.vector_store = "vs1"
    item.tools["code_interpreter"] = True
    item.tools["function"] = [{"name": "tool"}]

    data = item.to_dict()
    assert data["id"] == "a1"
    assert data["tool.code_interpreter"] is True
    assert data["tool.file_search"] is False
    assert data["tool.function"] == [{"name": "tool"}]

    item.reset()
    assert item.to_dict() == {
        "id": None,
        "name": None,
        "description": None,
        "instructions": None,
        "model": None,
        "meta": {},
        "files": {},
        "attachments": {},
        "vector_store": "",
        "tool.code_interpreter": False,
        "tool.file_search": False,
        "tool.function": [],
    }


def test_assistant_function_and_tool_management():
    item = AssistantItem()
    assert item.has_functions() is False
    assert item.has_tool("code_interpreter") is False
    assert item.has_tool("missing") is False

    item.add_function("weather", '{"city":"string"}', "Weather")
    assert item.has_functions() is True
    assert item.get_functions() == [{
        "name": "weather",
        "params": '{"city":"string"}',
        "desc": "Weather",
    }]

    item.tools["code_interpreter"] = True
    assert item.has_tool("code_interpreter") is True

    item.clear_functions()
    assert item.get_functions() == []

    item.tools["file_search"] = True
    item.add_function("x", "{}", "x")
    item.clear_tools()
    assert item.tools == {
        "code_interpreter": False,
        "file_search": False,
        "function": [],
    }


def test_assistant_file_management_is_idempotent():
    item = AssistantItem()
    assert item.has_file("f1") is False

    item.add_file("f1")
    assert item.has_file("f1") is True
    assert item.files["f1"] == {"id": "f1"}

    item.delete_file("missing")
    item.delete_file("f1")
    assert item.has_file("f1") is False

    item.add_file("f2")
    item.clear_files()
    assert item.files == {}


def test_assistant_attachment_management_is_idempotent():
    item = AssistantItem()
    attachment = AttachmentItem(id="att-1", name="a.txt")

    assert item.has_attachment("att-1") is False
    item.add_attachment(attachment)
    assert item.has_attachment("att-1") is True
    assert item.attachments["att-1"] is attachment

    item.delete_attachment("missing")
    item.delete_attachment("att-1")
    assert item.has_attachment("att-1") is False

    item.add_attachment(attachment)
    item.clear_attachments()
    assert item.attachments == {}


def test_assistant_dump_str_and_serialization_error():
    item = AssistantItem()
    item.id = "a1"
    assert json.loads(item.dump())["id"] == "a1"
    assert str(item) == item.dump()

    with patch("pygpt_net.item.assistant.json.dumps", side_effect=TypeError):
        assert item.dump() == ""
