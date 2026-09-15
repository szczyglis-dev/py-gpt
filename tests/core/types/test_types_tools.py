#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygpt_net.core.types.tools as tools


def setup_function():
    tools._REGISTERED_HIDDEN_TOOL_NAMES.clear()


def teardown_function():
    tools._REGISTERED_HIDDEN_TOOL_NAMES.clear()


def test_builtin_hidden_and_realtime_only_tools_are_classified_separately():
    assert tools.is_hidden_tool("delegate_task") is True
    assert tools.is_hidden_tool("mouse_click") is True
    assert tools.is_hidden_tool_realtime_only("mouse_click") is True
    assert tools.is_hidden_tool_realtime_only("delegate_task") is False
    assert tools.is_hidden_tool("ordinary_tool") is False


def test_register_hidden_tool_ignores_empty_values_and_registers_nonempty_name():
    tools.register_hidden_tool(None)
    tools.register_hidden_tool("   ")
    tools.register_hidden_tool("  private_tool  ")

    assert tools._REGISTERED_HIDDEN_TOOL_NAMES == {"private_tool"}
    assert tools.is_hidden_tool("private_tool") is True


def test_register_hidden_tool_definition_supports_cmd_name_and_function_shapes():
    tools.register_hidden_tool_definition({"hidden": True, "cmd": "cmd_tool"})
    tools.register_hidden_tool_definition({"hidden": True, "name": "named_tool"})
    tools.register_hidden_tool_definition({
        "hidden": True,
        "function": {"name": "function_tool"},
    })
    tools.register_hidden_tool_definition({"hidden": False, "cmd": "visible"})
    tools.register_hidden_tool_definition(None)

    assert tools.is_hidden_tool("cmd_tool") is True
    assert tools.is_hidden_tool("named_tool") is True
    assert tools.is_hidden_tool("function_tool") is True
    assert tools.is_hidden_tool("visible") is False


def test_hidden_tool_helpers_strip_names():
    tools.register_hidden_tool("trimmed")

    assert tools.is_hidden_tool(" trimmed ") is True
    assert tools.is_hidden_tool_realtime_only(" mouse_move ") is True
    assert tools.is_hidden_tool(None) is False
