#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pygpt_net.core.agents_v2.tools as tools_module
from pygpt_net.core.agents_v2.tools import WorkerToolFactory


class FakeFunctionTool:
    def __init__(self, async_fn=None, metadata=None, **kwargs):
        self.async_fn = async_fn
        self.metadata = metadata
        self.kwargs = kwargs

    @classmethod
    def from_defaults(cls, async_fn=None, name=None, description=None, **kwargs):
        return cls(
            async_fn=async_fn,
            metadata=SimpleNamespace(name=name, description=description),
            **kwargs,
        )


class FakeMetadata:
    def __init__(self, name, description, schema=None):
        self.name = name
        self.description = description
        self.schema = schema


def make_runtime(functions=None):
    runtime = SimpleNamespace()
    runtime.window = MagicMock()
    runtime.window.core.command.get_functions.return_value = list(functions or [])
    runtime.window.core.command.is_cmd.return_value = True
    runtime.window.core.debug = MagicMock()
    runtime.allow_local_tools = True
    runtime.shared_context_text = "shared text"
    runtime.index_id = None
    runtime.model = object()
    runtime.verbose = MagicMock()
    runtime.is_stopped = MagicMock(return_value=False)
    runtime.local_tool_lock = asyncio.Lock()
    runtime.emitter = SimpleNamespace(execute_plugin=AsyncMock(return_value={"ok": True}))
    runtime.emit_runtime_status = MagicMock()
    runtime.collect_artifacts = MagicMock()
    runtime.register_local_plugin_tool = MagicMock()
    runtime.record_local_plugin_tool_call = MagicMock(return_value="display-1")
    runtime.record_local_plugin_tool_result = MagicMock()
    return runtime


def make_worker(worker_id="w01"):
    return SimpleNamespace(
        id=worker_id,
        name="Worker",
        stop_requested=False,
        progress="",
        tool_ctx=SimpleNamespace(
            agent_call=False,
            async_disabled=True,
            internal=False,
            hidden=False,
            reply=True,
            results={"x": 1},
            extra={},
        ),
    )


def patch_tool_classes(monkeypatch):
    monkeypatch.setattr(tools_module, "FunctionTool", FakeFunctionTool)
    monkeypatch.setattr(tools_module, "SchemaToolMetadata", FakeMetadata)


def test_agents_v2_tool_factory_filters_reserved_and_invalid_plugin_specs(monkeypatch):
    patch_tool_classes(monkeypatch)
    runtime = make_runtime([
        {"name": "agent_create", "desc": "reserved", "params": "{}"},
        {"name": "normal_tool", "desc": "normal", "params": '{"type":"object"}'},
        {"name": "broken", "desc": "broken", "params": "not-json"},
    ])
    factory = WorkerToolFactory(runtime)

    tools = factory._plugin_tools(make_worker())

    assert [tool.metadata.name for tool in tools] == ["normal_tool"]
    runtime.register_local_plugin_tool.assert_called_once_with("normal_tool")
    runtime.window.core.debug.log.assert_called_once()


def test_agents_v2_tool_factory_plugin_call_normalizes_wrapped_arguments(monkeypatch):
    patch_tool_classes(monkeypatch)
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    runtime = make_runtime([
        {"name": "read_file", "desc": "Read file", "params": json.dumps(schema)},
    ])
    worker = make_worker()
    factory = WorkerToolFactory(runtime)
    tool = factory._plugin_tools(worker)[0]

    result = asyncio.run(tool.async_fn(params={"path": "/tmp/a.txt"}))

    assert result == json.dumps({"ok": True}, ensure_ascii=False, indent=2)
    runtime.record_local_plugin_tool_call.assert_called_once_with(
        "read_file", {"path": "/tmp/a.txt"}, actor="w01"
    )
    runtime.emitter.execute_plugin.assert_awaited_once_with(
        worker.tool_ctx,
        [{"cmd": "read_file", "params": {"path": "/tmp/a.txt"}}],
        runtime.is_stopped,
    )
    runtime.record_local_plugin_tool_result.assert_called_once_with(
        "display-1", "read_file", {"ok": True}, actor="w01"
    )
    assert worker.tool_ctx.agent_call is True
    assert worker.tool_ctx.async_disabled is False
    assert worker.tool_ctx.internal is True
    assert worker.tool_ctx.hidden is True
    assert worker.tool_ctx.reply is False
    runtime.collect_artifacts.assert_called_once_with(worker.tool_ctx, worker)


def test_agents_v2_tool_factory_plugin_call_rejects_missing_required_parameters(monkeypatch):
    patch_tool_classes(monkeypatch)
    schema = {"type": "object", "properties": {"query": {}}, "required": ["query"]}
    runtime = make_runtime([
        {"name": "search", "desc": "Search", "params": json.dumps(schema)},
    ])
    tool = WorkerToolFactory(runtime)._plugin_tools(make_worker())[0]

    result = json.loads(asyncio.run(tool.async_fn()))

    assert result["error"] == "Missing required tool parameter(s)."
    assert result["missing"] == ["query"]
    runtime.emitter.execute_plugin.assert_not_awaited()
    runtime.record_local_plugin_tool_call.assert_not_called()


def test_agents_v2_tool_factory_plugin_call_short_circuits_on_stop(monkeypatch):
    patch_tool_classes(monkeypatch)
    runtime = make_runtime([
        {"name": "tool_x", "desc": "Tool", "params": "{}"},
    ])
    runtime.is_stopped.return_value = True
    tool = WorkerToolFactory(runtime)._plugin_tools(make_worker())[0]

    result = asyncio.run(tool.async_fn(value=1))

    assert result == "Execution cancelled."
    runtime.emitter.execute_plugin.assert_not_awaited()


def test_agents_v2_tool_factory_records_error_response_before_reraising(monkeypatch):
    patch_tool_classes(monkeypatch)
    runtime = make_runtime([
        {"name": "failing_tool", "desc": "Tool", "params": "{}"},
    ])
    runtime.emitter.execute_plugin.side_effect = RuntimeError("boom")
    tool = WorkerToolFactory(runtime)._plugin_tools(make_worker())[0]

    try:
        asyncio.run(tool.async_fn())
        assert False, "RuntimeError was expected"
    except RuntimeError as exc:
        assert str(exc) == "boom"

    runtime.record_local_plugin_tool_result.assert_called_once_with(
        "display-1", "failing_tool", {"error": "boom"}, actor="w01"
    )


def test_agents_v2_tool_factory_build_adds_status_shared_context_and_plugin_tools(monkeypatch):
    patch_tool_classes(monkeypatch)
    runtime = make_runtime([
        {"name": "normal_tool", "desc": "Tool", "params": "{}"},
    ])
    factory = WorkerToolFactory(runtime)
    factory._rag_tool = MagicMock(return_value=None)

    tools = factory.build(make_worker())

    assert [tool.metadata.name for tool in tools] == [
        "normal_tool", "report_status", "shared_context"
    ]


def test_agents_v2_tool_factory_report_status_trims_and_emits():
    runtime = make_runtime()
    runtime.emit_worker_status = MagicMock()
    worker = make_worker()
    factory = WorkerToolFactory(runtime)

    result = asyncio.run(factory._report_status(worker, " x " * 200))

    assert result == "Status updated."
    assert len(worker.progress) == 240
    runtime.emit_worker_status.assert_called_once_with(worker, worker.progress)


def test_agents_v2_tool_factory_rag_tool_reuses_chat_index(monkeypatch):
    runtime = make_runtime()
    runtime.index_id = "idx-1"
    runtime.window.core.idx.is_valid.return_value = True
    query_engine = object()
    index = MagicMock()
    index.as_query_engine.return_value = query_engine
    runtime.window.core.idx.chat.get_index.return_value = (index, object())
    captured = {}

    class FakeQueryEngineTool:
        def __init__(self, query_engine, metadata):
            captured["query_engine"] = query_engine
            captured["metadata"] = metadata

    monkeypatch.setattr(tools_module, "QueryEngineTool", FakeQueryEngineTool)
    monkeypatch.setattr(tools_module, "ToolMetadata", lambda name, description: SimpleNamespace(
        name=name, description=description
    ))

    tool = WorkerToolFactory(runtime)._rag_tool()

    assert isinstance(tool, FakeQueryEngineTool)
    assert captured["query_engine"] is query_engine
    assert captured["metadata"].name == "query_index"
    assert "idx-1" in captured["metadata"].description
    index.as_query_engine.assert_called_once_with(similarity_top_k=3)
