#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime


def make_runtime(enabled=True, extra=None):
    runtime = AgentsV2Runtime.__new__(AgentsV2Runtime)
    runtime.return_tool_calls_to_main_ctx = enabled
    runtime._main_tool_calls = []
    runtime._main_tool_call_seq = 0
    runtime._local_plugin_tool_names = set()
    runtime.run_id = "run123"
    main = SimpleNamespace(extra={} if extra is None else extra)
    runtime.context = SimpleNamespace(ctx=main)
    runtime.window = MagicMock()
    return runtime, main


def test_agents_v2_runtime_tool_value_conversion_is_persistence_safe():
    assert AgentsV2Runtime._json_safe_tool_value('{"x": 1}') == {"x": 1}
    assert AgentsV2Runtime._json_safe_tool_value("plain") == "plain"
    assert AgentsV2Runtime._json_safe_tool_value(None) == {}
    assert AgentsV2Runtime._json_safe_tool_result('[1, 2]') == [1, 2]
    assert AgentsV2Runtime._json_safe_tool_result("") == ""


def test_agents_v2_runtime_local_tool_call_unwraps_params_and_attaches_response():
    runtime, _main = make_runtime(True)

    call_id = runtime.record_local_plugin_tool_call(
        "read_file", {"params": {"path": "a.txt"}}, actor="w01"
    )
    runtime.record_local_plugin_tool_result(
        call_id, "read_file", '{"content":"ok"}', actor="w01"
    )

    assert call_id == "agents_v2_run123_1"
    assert runtime._main_tool_calls == [{
        "id": call_id,
        "call_id": call_id,
        "type": "function",
        "function": {"name": "read_file", "arguments": {"path": "a.txt"}},
        "agents_v2_actor": "w01",
        "agents_v2_response": {"content": "ok"},
    }]


def test_agents_v2_runtime_normal_tool_events_pair_by_provider_call_id():
    runtime, _main = make_runtime(True)

    runtime.record_tool_call({
        "tool_name": "query_index",
        "tool_kwargs": {"query": "first"},
        "tool_id": "call-a",
    }, actor="orchestrator")
    runtime.record_tool_call({
        "tool_name": "query_index",
        "tool_kwargs": {"query": "second"},
        "tool_id": "call-b",
    }, actor="orchestrator")
    runtime.record_tool_result({
        "tool_name": "query_index",
        "tool_output": {"content": "B"},
        "tool_id": "call-b",
    }, actor="orchestrator")
    runtime.record_tool_result({
        "tool_name": "query_index",
        "tool_output": {"content": "A"},
        "tool_id": "call-a",
    }, actor="orchestrator")

    assert [item["agents_v2_response"] for item in runtime._main_tool_calls] == ["A", "B"]


def test_agents_v2_runtime_result_without_call_id_matches_oldest_unanswered_same_tool():
    runtime, _main = make_runtime(True)
    runtime.record_tool_call({"tool_name": "search", "tool_kwargs": {"q": 1}}, actor="w01")
    runtime.record_tool_call({"tool_name": "search", "tool_kwargs": {"q": 2}}, actor="w01")

    runtime.record_tool_result({"tool_name": "search", "tool_output": "one"}, actor="w01")
    runtime.record_tool_result({"tool_name": "search", "tool_output": "two"}, actor="w01")

    assert [item["agents_v2_response"] for item in runtime._main_tool_calls] == ["one", "two"]


def test_agents_v2_runtime_excludes_orchestration_and_registered_local_tools_from_event_capture():
    runtime, _main = make_runtime(True)
    runtime.register_local_plugin_tool("save_file")

    runtime.record_tool_call({"tool_name": "agent_create", "tool_kwargs": {}}, actor="orchestrator")
    runtime.record_tool_call({"tool_name": "save_file", "tool_kwargs": {"path": "x"}}, actor="w01")
    runtime.record_tool_call({"tool_name": "query_index", "tool_kwargs": {"query": "x"}}, actor="w01")

    assert [item["function"]["name"] for item in runtime._main_tool_calls] == ["query_index"]


def test_agents_v2_runtime_export_tool_chain_replaces_previous_display_chain():
    runtime, main = make_runtime(True, {
        "tool_calls": [{"id": "old"}],
        "agents_v2_tool_calls_display": True,
        "other": 7,
    })
    runtime._main_tool_calls = [{"id": "new", "function": {"name": "search", "arguments": {}}}]

    runtime.export_tool_calls_to_main_ctx()

    assert main.extra["tool_calls"] == runtime._main_tool_calls
    assert main.extra["agents_v2_tool_calls_display"] is True
    assert main.extra["other"] == 7
    runtime.window.core.ctx.update_item.assert_called_once_with(main)


def test_agents_v2_runtime_export_disabled_removes_only_agents_v2_owned_chain():
    runtime, main = make_runtime(False, {
        "tool_calls": [{"id": "old"}],
        "agents_v2_tool_calls_display": True,
        "other": "keep",
    })

    runtime.export_tool_calls_to_main_ctx()

    assert main.extra == {"other": "keep"}
    runtime.window.core.ctx.update_item.assert_called_once_with(main)


def test_agents_v2_runtime_export_disabled_preserves_foreign_tool_data():
    foreign = [{"id": "foreign"}]
    runtime, main = make_runtime(False, {"tool_calls": foreign, "other": 1})

    runtime.export_tool_calls_to_main_ctx()

    assert main.extra["tool_calls"] is foreign
    runtime.window.core.ctx.update_item.assert_not_called()


def test_agents_v2_runtime_empty_new_chain_clears_previous_agents_v2_display():
    runtime, main = make_runtime(True, {
        "tool_calls": [{"id": "old"}],
        "agents_v2_tool_calls_display": True,
    })

    runtime.export_tool_calls_to_main_ctx()

    assert "tool_calls" not in main.extra
    assert "agents_v2_tool_calls_display" not in main.extra
    runtime.window.core.ctx.update_item.assert_called_once_with(main)
