#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pygpt_net.core.agents.custom.schema import parse_schema


def test_parse_schema_builds_all_supported_node_types_and_nested_slots():
    schema = [
        {
            "id": "agent-1",
            "type": "agent",
            "slots": {
                "name": "Coder",
                "instruction": "Code",
                "role": "implementation",
                "remote_tools": False,
                "local_tools": True,
                "output": {"out": ["end-1"]},
                "input": {"in": ["start-1"]},
                "memory": {"out": ["mem-1"], "in": ["mem-1"]},
            },
        },
        {"id": "start-1", "type": "start", "slots": {"output": {"out": ["agent-1"]}}},
        {"id": "end-1", "type": "end", "slots": {"input": {"in": ["agent-1"]}}},
        {"id": "mem-1", "type": "memory", "slots": {"name": "Memory", "input": {"in": ["agent-1"]}}},
    ]

    result = parse_schema(schema)

    agent = result.agents["agent-1"]
    assert agent.name == "Coder"
    assert agent.instruction == "Code"
    assert agent.role == "implementation"
    assert agent.allow_remote_tools is False
    assert agent.allow_local_tools is True
    assert agent.outputs == ["end-1"]
    assert agent.inputs == ["start-1"]
    assert agent.memory_out == "mem-1"
    assert agent.memory_in == ["mem-1"]
    assert result.starts["start-1"].outputs == ["agent-1"]
    assert result.ends["end-1"].inputs == ["agent-1"]
    assert result.memories["mem-1"].agents == ["agent-1"]


def test_parse_schema_uses_safe_defaults_and_ignores_unknown_node_types():
    result = parse_schema([
        {"id": "agent", "type": "agent", "slots": None},
        {"id": "unknown", "type": "other", "slots": {}},
    ])

    agent = result.agents["agent"]
    assert agent.name == ""
    assert agent.instruction == ""
    assert agent.allow_remote_tools is True
    assert agent.allow_local_tools is True
    assert agent.outputs == []
    assert agent.inputs == []
    assert agent.memory_out is None
    assert "unknown" not in result.agents


def test_safe_get_walks_nested_dict_and_returns_default_on_missing_or_non_dict():
    from pygpt_net.core.agents.custom.schema import _safe_get

    data = {"a": {"b": 3}}
    assert _safe_get(data, "a", "b", default=0) == 3
    assert _safe_get(data, "a", "missing", default=7) == 7
    assert _safe_get({"a": 1}, "a", "b", default=9) == 9
