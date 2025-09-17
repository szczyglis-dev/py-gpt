#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #
from unittest.mock import MagicMock

import pytest
import json
from types import SimpleNamespace
from pygpt_net.provider.api.openai.agents.remote_tools import is_computer_tool, append_tools, get_remote_tools
import pygpt_net.provider.api.openai.agents.remote_tools as tools
from agents import ModelSettings

class DummyModel:
    def __init__(self, id, is_gpt_value=True):
        self.id = id
        self._is_gpt = is_gpt_value
    def is_gpt(self):
        return self._is_gpt

class DummyPreset:
    def __init__(self, remote_tools):
        self.remote_tools = remote_tools

class DummyConfig:
    def __init__(self, settings):
        self.settings = settings
    def get(self, key, default=None):
        return self.settings.get(key, default)

class DummyCore:
    def __init__(self, settings):
        self.config = DummyConfig(settings)

class DummyWindow:
    def __init__(self, settings):
        self.core = DummyCore(settings)
        self.controller = SimpleNamespace(chat=SimpleNamespace(remote_tools=SimpleNamespace(enabled=MagicMock(return_value=True))))

def test_is_computer_tool_non_gpt():
    model = DummyModel("any", False)
    preset = DummyPreset("a,b")
    window = object()
    assert is_computer_tool(window, model, preset, False) is False

def test_is_computer_tool_non_expert_true():
    model = DummyModel("computer-use-xyz", True)
    preset = DummyPreset("irrelevant")
    window = object()
    assert is_computer_tool(window, model, preset, False) is True

def test_is_computer_tool_non_expert_false():
    model = DummyModel("not-computer", True)
    preset = DummyPreset("irrelevant")
    window = object()
    assert is_computer_tool(window, model, preset, False) is False

def test_is_computer_tool_expert_true():
    model = DummyModel("computer-use-123", True)
    preset = DummyPreset(" computer_use , code_interpreter")
    window = object()
    assert is_computer_tool(window, model, preset, True) is True

def test_is_computer_tool_expert_false():
    model = DummyModel("computer-use-123", True)
    preset = DummyPreset("web_search")
    window = object()
    assert is_computer_tool(window, model, preset, True) is False

def test_is_computer_tool_expert_none_preset():
    model = DummyModel("computer-use-123", True)
    window = object()
    assert is_computer_tool(window, model, None, True) is None

def test_is_computer_tool_expert_empty_preset():
    model = DummyModel("computer-use-123", True)
    preset = DummyPreset("")
    window = object()
    assert is_computer_tool(window, model, preset, True) is None

def test_append_tools_all_allowed(monkeypatch):
    def dummy_get_remote_tools(window, model, preset, is_expert_call):
        return ["remote1", "remote2"]
    def dummy_is_computer_tool(window, model, preset, is_expert_call):
        return True
    monkeypatch.setattr(tools, "get_remote_tools", dummy_get_remote_tools)
    monkeypatch.setattr(tools, "is_computer_tool", dummy_is_computer_tool)
    model = DummyModel("computer-use-123", True)
    preset = DummyPreset("any")
    window = object()
    local_tools = ["local1"]
    result = append_tools(local_tools, window, model, preset, True, True, False)
    assert result.get("model_settings") == ModelSettings(truncation="auto")
    assert result.get("tools") == ["remote1", "remote2", "local1"]

def test_append_tools_no_local(monkeypatch):
    def dummy_get_remote_tools(window, model, preset, is_expert_call):
        return ["remote1"]
    def dummy_is_computer_tool(window, model, preset, is_expert_call):
        return True
    monkeypatch.setattr(tools, "get_remote_tools", dummy_get_remote_tools)
    monkeypatch.setattr(tools, "is_computer_tool", dummy_is_computer_tool)
    model = DummyModel("computer-use-123", True)
    preset = DummyPreset("any")
    window = object()
    local_tools = ["local1"]
    result = append_tools(local_tools, window, model, preset, False, True, False)
    assert result.get("model_settings") == ModelSettings(truncation="auto")
    assert result.get("tools") == ["remote1"]

def test_append_tools_no_remote(monkeypatch):
    def dummy_get_remote_tools(window, model, preset, is_expert_call):
        return ["remote1"]
    def dummy_is_computer_tool(window, model, preset, is_expert_call):
        return True
    monkeypatch.setattr(tools, "get_remote_tools", dummy_get_remote_tools)
    monkeypatch.setattr(tools, "is_computer_tool", dummy_is_computer_tool)
    model = DummyModel("computer-use-123", True)
    preset = DummyPreset("any")
    window = object()
    local_tools = ["local1"]
    result = append_tools(local_tools, window, model, preset, True, False, False)
    assert "model_settings" not in result
    assert result.get("tools") == ["local1"]

def test_append_tools_empty(monkeypatch):
    def dummy_get_remote_tools(window, model, preset, is_expert_call):
        return []
    def dummy_is_computer_tool(window, model, preset, is_expert_call):
        return False
    monkeypatch.setattr(tools, "get_remote_tools", dummy_get_remote_tools)
    monkeypatch.setattr(tools, "is_computer_tool", dummy_is_computer_tool)
    model = DummyModel("id", True)
    preset = DummyPreset("any")
    window = object()
    local_tools = []
    result = append_tools(local_tools, window, model, preset, True, True, False)
    assert result == {}

def test_get_remote_tools_not_gpt():
    model = DummyModel("any", False)
    preset = DummyPreset("irrelevant")
    window = DummyWindow({})
    result = get_remote_tools(window, model, preset, False)
    assert result == []

def test_get_remote_tools_id_starts_o1():
    model = DummyModel("o1-model", True)
    preset = DummyPreset("irrelevant")
    window = DummyWindow({})
    result = get_remote_tools(window, model, preset, False)
    assert result == []

def test_get_remote_tools_non_expert_enabled(monkeypatch):
    dummy_web_search = lambda: "web_search_tool"
    dummy_code_interpreter = lambda tool_config: "code_interpreter_tool"
    dummy_image = lambda tool_config: "image_tool"
    dummy_file_search = lambda max_num_results, vector_store_ids, include_search_results: "file_search_tool"
    dummy_mcp = lambda tool_config: "mcp_tool"
    monkeypatch.setattr(tools, "WebSearchTool", lambda: dummy_web_search())
    monkeypatch.setattr(tools, "CodeInterpreterTool", lambda tool_config: dummy_code_interpreter(tool_config))
    monkeypatch.setattr(tools, "ImageGenerationTool", lambda tool_config: dummy_image(tool_config))
    monkeypatch.setattr(tools, "FileSearchTool", lambda max_num_results, vector_store_ids, include_search_results: dummy_file_search(max_num_results, vector_store_ids, include_search_results))
    monkeypatch.setattr(tools, "HostedMCPTool", lambda tool_config: dummy_mcp(tool_config))
    settings = {
       "remote_tools.web_search": True,
       "remote_tools.image": True,
       "remote_tools.code_interpreter": True,
       "remote_tools.mcp": True,
       "remote_tools.file_search": True,
       "remote_tools.file_search.args": "store1, store2",
       "remote_tools.mcp.args": '{"param": "value"}'
    }
    window = DummyWindow(settings)
    model = DummyModel("normal-model", True)
    preset = DummyPreset("irrelevant")
    result = get_remote_tools(window, model, preset, False)
    assert result == ["web_search_tool", "code_interpreter_tool", "image_tool", "file_search_tool", "mcp_tool"]

def test_get_remote_tools_non_expert_disabled(monkeypatch):
    dummy_web_search = lambda: "web_search_tool"
    monkeypatch.setattr(tools, "WebSearchTool", lambda: dummy_web_search())
    settings = {
       "remote_tools.web_search": False,
       "remote_tools.image": False,
       "remote_tools.code_interpreter": False,
       "remote_tools.mcp": False,
       "remote_tools.file_search": False,
    }
    window = DummyWindow(settings)
    window.controller.chat.remote_tools.enabled = MagicMock(return_value=False)
    model = DummyModel("normal-model", True)
    preset = DummyPreset("irrelevant")
    result = get_remote_tools(window, model, preset, False)
    assert result == []

def test_get_remote_tools_expert_computer(monkeypatch):
    dummy_computer = lambda window: "local_computer"
    dummy_computer_tool = lambda computer, on_safety_check: ("computer_tool", computer, on_safety_check)
    monkeypatch.setattr(tools, "LocalComputer", lambda window: dummy_computer(window))
    monkeypatch.setattr(tools, "ComputerTool", lambda computer, on_safety_check: dummy_computer_tool(computer, on_safety_check))
    monkeypatch.setattr(tools, "OPENAI_REMOTE_TOOL_DISABLE_COMPUTER_USE", [])
    settings = {}
    window = DummyWindow(settings)
    model = DummyModel("computer-use-model", True)
    preset = DummyPreset("computer_use, code_interpreter")
    result = get_remote_tools(window, model, preset, True)
    assert len(result) == 1
    comp_tool = result[0]
    assert comp_tool[0] == "computer_tool"
    assert comp_tool[1] == "local_computer"
    assert callable(comp_tool[2])

def test_get_remote_tools_expert_web_search(monkeypatch):
    dummy_web_search = lambda: "web_search_tool"
    monkeypatch.setattr(tools, "WebSearchTool", lambda: dummy_web_search())
    settings = {}
    window = DummyWindow(settings)
    model = DummyModel("model", True)
    preset = DummyPreset("web_search")
    result = get_remote_tools(window, model, preset, True)
    assert result == ["web_search_tool"]

def test_get_remote_tools_expert_empty_preset(monkeypatch):
    settings = {}
    window = DummyWindow(settings)
    model = DummyModel("model", True)
    preset = DummyPreset("")
    result = get_remote_tools(window, model, preset, True)
    assert result == []
    result = get_remote_tools(window, model, None, True)
    assert result == []