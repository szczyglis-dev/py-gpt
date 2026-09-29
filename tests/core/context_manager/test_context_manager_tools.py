#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.context_manager.tools as tools_module


class FakeFunctionTool:
    @classmethod
    def from_defaults(cls, **kwargs):
        return SimpleNamespace(**kwargs)


def test_build_context_tools_exposes_core_conversation_memory_tools(monkeypatch):
    monkeypatch.setattr(tools_module, "FunctionTool", FakeFunctionTool)
    manager = MagicMock()
    manager.get_notes.return_value = "existing"
    manager.add_notes.return_value = "existing\nadded"
    manager.replace_notes.return_value = "replacement"
    ctx = object()

    tools = tools_module.build_context_tools(manager, ctx)

    assert [tool.name for tool in tools] == [
        "memory_ctx_get",
        "memory_ctx_add",
        "memory_ctx_replace",
    ]
    assert set(tools_module.CONTEXT_TOOL_NAMES) == {tool.name for tool in tools}
    assert asyncio.run(tools[0].async_fn()) == "existing"
    assert asyncio.run(tools[1].async_fn("added")) == "existing\nadded"
    assert asyncio.run(tools[2].async_fn("replacement")) == "replacement"
    manager.get_notes.assert_called_once_with(ctx)
    manager.add_notes.assert_called_once_with(ctx, "added")
    manager.replace_notes.assert_called_once_with(ctx, "replacement")


def test_memory_ctx_get_has_clear_empty_state_message(monkeypatch):
    monkeypatch.setattr(tools_module, "FunctionTool", FakeFunctionTool)
    manager = MagicMock()
    manager.get_notes.return_value = ""

    tool = tools_module.build_context_tools(manager, object())[0]

    assert asyncio.run(tool.async_fn()) == "No continuation notes are stored for this conversation."
