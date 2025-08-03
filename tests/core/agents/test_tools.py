#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import json
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock

from pygpt_net.core.agents.tools import Tools, PluginToolMetadata, CodeExecutor

@pytest.fixture
def fake_window():
    window = MagicMock()
    window.core = MagicMock()
    # Setup idx services.
    window.core.idx = MagicMock()
    window.core.idx.llm = MagicMock()
    window.core.idx.llm.get_service_context.return_value = ("llm_service", "embed_service")
    def storage_get(idx, llm, embed):
        if idx == "valid":
            fake_index = MagicMock()
            fake_query_engine = MagicMock()
            fake_query_engine.query = lambda q: "fake query result"
            fake_index.as_query_engine = lambda similarity_top_k: fake_query_engine
            return fake_index
        return None
    window.core.idx.storage = MagicMock()
    window.core.idx.storage.get.side_effect = storage_get

    # Setup command functions.
    window.core.command = MagicMock()
    window.core.command.get_functions.return_value = [
        {
            "name": "test_function",
            "desc": "Test description",
            "params": json.dumps({
                "properties": {"x": {"type": "number"}},
                "required": ["x"]
            })
        }
    ]
    window.core.debug = MagicMock()
    window.core.debug.add = MagicMock()
    window.core.filesystem = MagicMock()
    window.core.filesystem.parser = MagicMock()
    window.core.filesystem.parser.extract_data_files = MagicMock()

    # Setup controller plugins and command dispatcher.
    window.controller = MagicMock()
    window.controller.plugins = MagicMock()
    window.controller.plugins.apply_cmds_all.return_value = "applied command"
    window.controller.command = MagicMock()
    window.controller.command.dispatch_only = MagicMock()

    window.core.agents = SimpleNamespace(tools=SimpleNamespace(last_tool_output=None))
    return window

@pytest.fixture
def tools_instance(fake_window):
    return Tools(window=fake_window)

@pytest.fixture
def fake_context():
    return SimpleNamespace(model="test_model", ctx="test_ctx")

@pytest.fixture
def fake_ctx_item():
    return SimpleNamespace(extra={})

# Corrected test: check tool metadata name instead of its string representation.
def test_prepare_without_agent_idx(tools_instance, fake_context):
    extra = {"agent_idx": "_"}
    tools_list = tools_instance.prepare(fake_context, extra, verbose=False, force=False)
    assert any(hasattr(tool, "metadata") and tool.metadata.name == "test_function"
               for tool in tools_list)

def test_prepare_with_valid_agent_idx(tools_instance, fake_context):
    extra = {"agent_idx": "valid"}
    tools_list = tools_instance.prepare(fake_context, extra, verbose=False, force=False)
    names = [tool.metadata.name for tool in tools_list if hasattr(tool, "metadata")]
    assert "test_function" in names
    assert "query_engine" in names

def test_get_plugin_functions(tools_instance, fake_ctx_item):
    tools_list = tools_instance.get_plugin_functions(fake_ctx_item, verbose=False, force=False)
    assert len(tools_list) > 0
    tool = tools_list[0]
    output = tool.fn(x=42)
    assert "applied command" in output

def test_tool_exec_normal(tools_instance):
    result = tools_instance.tool_exec("normal_cmd", {"param": 1})
    assert result == "applied command"

def test_tool_exec_query_engine_missing_query(tools_instance):
    tools_instance.context = SimpleNamespace(model="test_model")
    tools_instance.agent_idx = "valid"
    result = tools_instance.tool_exec("query_engine", {})
    assert result == "Query parameter is required for query_engine tool."

def test_tool_exec_query_engine_context_none(tools_instance):
    tools_instance.context = None
    tools_instance.agent_idx = "valid"
    result = tools_instance.tool_exec("query_engine", {"query": "search"})
    assert result == "Context is not set for query_engine tool."

def test_tool_exec_query_engine_agent_idx_missing(tools_instance, fake_context):
    tools_instance.context = fake_context
    tools_instance.agent_idx = None
    result = tools_instance.tool_exec("query_engine", {"query": "search"})
    assert result == "Agent index is not set for query_engine tool."
    tools_instance.agent_idx = "_"
    result = tools_instance.tool_exec("query_engine", {"query": "search"})
    assert result == "Agent index is not set for query_engine tool."

def test_tool_exec_query_engine_index_not_found(tools_instance, fake_context):
    tools_instance.context = fake_context
    tools_instance.agent_idx = "invalid"
    result = tools_instance.tool_exec("query_engine", {"query": "search"})
    assert result == "Index not found for query_engine tool."

def test_tool_exec_query_engine_success(tools_instance, fake_context):
    tools_instance.context = fake_context
    tools_instance.agent_idx = "valid"
    result = tools_instance.tool_exec("query_engine", {"query": "search"})
    assert result == "fake query result"

def test_get_plugin_specs(tools_instance, fake_context):
    tools_instance.agent_idx = "valid"
    specs = tools_instance.get_plugin_specs(fake_context, {})
    assert any("query_engine" in spec for spec in specs)
    assert any("test_function" in spec for spec in specs)

def test_last_tool_output_methods(tools_instance):
    assert tools_instance.get_last_tool_output() == {}
    tools_instance.last_tool_output = {"dummy": 123}
    assert tools_instance.get_last_tool_output() == {"dummy": 123}
    assert tools_instance.has_last_tool_output() is True
    tools_instance.clear_last_tool_output()
    assert tools_instance.get_last_tool_output() == {}
    assert tools_instance.has_last_tool_output() is False

def test_append_tool_outputs(tools_instance, fake_window):
    sample_output = {"code": {"output": {"content": "sample content"}}}
    tools_instance.last_tool_output = sample_output
    fake_ctx = SimpleNamespace(extra={})
    tools_instance.append_tool_outputs(fake_ctx, clear=True)
    assert fake_ctx.extra.get("tool_output") == [sample_output]
    fake_window.core.filesystem.parser.extract_data_files.assert_called_with(fake_ctx, "sample content")
    assert tools_instance.last_tool_output is None

def test_extract_tool_outputs(tools_instance, fake_window):
    sample_output = {"code": {"output": {"content": "extracted content"}}}
    tools_instance.last_tool_output = sample_output
    fake_ctx = SimpleNamespace(extra={})
    tools_instance.extract_tool_outputs(fake_ctx, clear=True)
    fake_window.core.filesystem.parser.extract_data_files.assert_called_with(fake_ctx, "extracted content")
    assert tools_instance.last_tool_output is None

def test_log(tools_instance, fake_window):
    tools_instance.verbose = True
    tools_instance.log("test log")
    fake_window.core.debug.add.assert_called_with("test log")

def test_plugin_tool_metadata_get_parameters_dict():
    schema = {
        "type": "object",
        "properties": {"x": {"type": "number"}},
        "required": ["x"],
        "extra": "ignore"
    }
    meta = PluginToolMetadata("name", "desc")
    meta.schema = schema
    params = meta.get_parameters_dict()
    assert "type" in params
    assert "properties" in params
    assert "required" in params
    assert "extra" not in params

def test_code_executor_restart(fake_window):
    executor = CodeExecutor(window=fake_window)
    output = executor.execute("/restart")
    assert output == "IPython kernel restarted successfully."

def test_code_executor_execute(fake_window):
    def fake_dispatch(event):
        event.ctx.bag = {
            "code": {
                "input": {"content": "dummy input"},
                "output": {"content": "dummy output"}
            },
            "plugin": "dummy plugin",
            "result": "dummy result"
        }
    fake_window.controller.command.dispatch_only.side_effect = fake_dispatch
    executor = CodeExecutor(window=fake_window)
    output = executor.execute("print('hello')")
    assert output == "dummy output"
    tool_output = fake_window.core.agents.tools.last_tool_output
    assert tool_output is not None
    assert tool_output.get("cmd") == "ipython_execute"
    inner_output = tool_output.get("code", {}).get("output", {}).get("content")
    assert inner_output == "dummy output"