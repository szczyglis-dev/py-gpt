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

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pygpt_net.core.types import MODE_COMPUTER
import pygpt_net.provider.api.openai.remote_tools as remote_mod
from pygpt_net.provider.api.openai.remote_tools import RemoteTools

class DummyConfig:
    def __init__(self, data):
        self.data = data
    def get(self, key, default=None):
        return self.data.get(key, default)

def get_dummy_window(config_data):
    dummy_config = DummyConfig(config_data)
    dummy_computer = SimpleNamespace(get_tool=lambda: {"type": "computer_tool"})
    core = SimpleNamespace(config=dummy_config, api=SimpleNamespace(openai=SimpleNamespace(computer=dummy_computer)))
    controller = SimpleNamespace(chat=SimpleNamespace(remote_tools=SimpleNamespace(enabled=MagicMock(return_value=True))))
    return SimpleNamespace(core=core, controller=controller)

def set_disable(monkeypatch):
    monkeypatch.setattr(remote_mod, "OPENAI_REMOTE_TOOL_DISABLE_COMPUTER_USE", [])
    monkeypatch.setattr(remote_mod, "OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH", [])
    monkeypatch.setattr(remote_mod, "OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER", [])
    monkeypatch.setattr(remote_mod, "OPENAI_REMOTE_TOOL_DISABLE_IMAGE", [])
    monkeypatch.setattr(remote_mod, "OPENAI_REMOTE_TOOL_DISABLE_FILE_SEARCH", [])
    monkeypatch.setattr(remote_mod, "OPENAI_REMOTE_TOOL_DISABLE_MCP", [])

def test_get_choices(monkeypatch):
    monkeypatch.setattr(remote_mod, "trans", lambda s: s.upper())
    rt = RemoteTools()
    expected = [
        {"web_search": "REMOTE_TOOL.OPENAI.WEB_SEARCH"},
        {"image": "REMOTE_TOOL.OPENAI.IMAGE"},
        {"code_interpreter": "REMOTE_TOOL.OPENAI.CODE_INTERPRETER"},
        {"mcp": "REMOTE_TOOL.OPENAI.MCP"},
        {"file_search": "REMOTE_TOOL.OPENAI.FILE_SEARCH"},
        {"computer_use": "REMOTE_TOOL.OPENAI.COMPUTER_USE"},
    ]
    assert rt.get_choices() == expected

@pytest.mark.parametrize("model_id", ["o1_model", "o3_model"])
def test_append_to_tools_o_versions(model_id):
    dummy_window = get_dummy_window({})
    rt = RemoteTools(window=dummy_window)
    tools = ["existing"]
    model = SimpleNamespace(id=model_id)
    result = rt.append_to_tools(mode="any", model=model, stream=False, is_expert_call=False, tools=tools.copy())
    assert result == tools

def test_append_to_tools_expert(monkeypatch):
    set_disable(monkeypatch)
    config_data = {"remote_tools.file_search.args": "", "remote_tools.mcp.args": ""}
    dummy_window = get_dummy_window(config_data)
    rt = RemoteTools(window=dummy_window)
    model = SimpleNamespace(id="test_model_expert")
    preset = SimpleNamespace(remote_tools="web_search, image")
    result = rt.append_to_tools(mode="any", model=model, stream=True, is_expert_call=True, tools=[], preset=preset)
    expected = [
        {"type": "web_search_preview"},
        {"type": "image_generation", "partial_images": 1},
    ]
    assert result == expected

def test_append_to_tools_non_expert_computer(monkeypatch):
    set_disable(monkeypatch)
    dummy_window = get_dummy_window({})
    rt = RemoteTools(window=dummy_window)
    model = SimpleNamespace(id="test_model_normal_computer")
    result = rt.append_to_tools(mode=MODE_COMPUTER, model=model, stream=False, is_expert_call=False, tools=[])
    expected = [{"type": "computer_tool"}]
    assert result == expected

def test_append_to_tools_non_expert_normal(monkeypatch):
    set_disable(monkeypatch)
    config_data = {
        "remote_tools.web_search": True,
        "remote_tools.image": True,
        "remote_tools.code_interpreter": True,
        "remote_tools.mcp": True,
        "remote_tools.file_search": True,
        "remote_tools.file_search.args": "store1, store2",
        "remote_tools.mcp.args": '{"type": "mcp_tool"}',
    }
    dummy_window = get_dummy_window(config_data)
    rt = RemoteTools(window=dummy_window)
    model = SimpleNamespace(id="test_model_normal")
    result = rt.append_to_tools(mode="regular", model=model, stream=True, is_expert_call=False, tools=[])
    expected = [
        {"type": "web_search_preview"},
        {"type": "code_interpreter", "container": {"type": "auto"}},
        {"type": "image_generation", "partial_images": 1},
        {"type": "file_search", "vector_store_ids": ["store1", "store2"]},
        {"type": "mcp_tool"},
    ]
    assert result == expected

def test_append_to_tools_non_expert_empty_args(monkeypatch):
    set_disable(monkeypatch)
    config_data = {
        "remote_tools.web_search": True,
        "remote_tools.image": True,
        "remote_tools.code_interpreter": True,
        "remote_tools.mcp": True,
        "remote_tools.file_search": True,
        "remote_tools.file_search.args": "",
        "remote_tools.mcp.args": "",
    }
    dummy_window = get_dummy_window(config_data)
    rt = RemoteTools(window=dummy_window)
    model = SimpleNamespace(id="test_model_empty_args")
    result = rt.append_to_tools(mode="regular", model=model, stream=False, is_expert_call=False, tools=[])
    expected = [
        {"type": "web_search_preview"},
        {"type": "code_interpreter", "container": {"type": "auto"}},
        {"type": "image_generation"},
    ]
    assert result == expected

def test_append_to_tools_expert_with_unknown(monkeypatch):
    set_disable(monkeypatch)
    config_data = {"remote_tools.file_search.args": "", "remote_tools.mcp.args": ""}
    dummy_window = get_dummy_window(config_data)
    rt = RemoteTools(window=dummy_window)
    model = SimpleNamespace(id="test_model_expert_unknown")
    preset = SimpleNamespace(remote_tools=" web_search , code_interpreter,unknown_tool")
    result = rt.append_to_tools(mode="any", model=model, stream=False, is_expert_call=True, tools=[], preset=preset)
    expected = [
        {"type": "web_search_preview"},
        {"type": "code_interpreter", "container": {"type": "auto"}},
    ]
    assert result == expected