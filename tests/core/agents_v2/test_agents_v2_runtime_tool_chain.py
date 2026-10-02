#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime
from pygpt_net.core.agents_v2.mode import AgentMode
from pygpt_net.core.agents_v2.strategy import get_agent_strategy
from pygpt_net.core.agents_v2.timeline import RuntimeTimeline
from pygpt_net.core.agents_v2.tool_history import RuntimeToolHistory
from pygpt_net.core.agents_v2.utils import json_safe_tool_result, json_safe_tool_value
from pygpt_net.core.types.tools import is_hidden_tool


def make_runtime(enabled=True, extra=None):
    runtime = AgentsV2Runtime.__new__(AgentsV2Runtime)
    runtime.tool_history = RuntimeToolHistory(runtime)
    runtime.timeline = RuntimeTimeline(runtime)
    runtime.agent_mode = AgentMode.ORCHESTRATOR
    runtime.agent_definition = None
    runtime.strategy = get_agent_strategy(runtime.agent_mode)
    runtime.return_tool_calls_to_main_ctx = enabled
    runtime.workers = SimpleNamespace(states={}, parent_parts={})
    runtime.run_id = "run123"

    part = SimpleNamespace(
        agent_id="orchestrator",
        name="Orchestrator",
        extra={},
        output="",
        tasks=[],
        uuid="part-1",
    )
    main = SimpleNamespace(extra={} if extra is None else extra, parts=[part], active_part=part)
    runtime.context = SimpleNamespace(ctx=main)
    runtime.window = MagicMock()
    runtime.window.core.command.is_tool_hidden.side_effect = is_hidden_tool
    runtime.timeline.parts["orchestrator"] = part

    def record_tool_calls(_main, calls, part=None, agent_id=None, agent_name=None,
                          task_name=None, **_kwargs):
        call = calls[0]
        task = SimpleNamespace(
            extra={},
            agent_id=agent_id,
            task_name=task_name,
            tool_call_id=call.get("call_id") or call.get("id"),
            tool_output=None,
            output="",
            task_summary="",
            touch=MagicMock(),
            mark_ui_ready=MagicMock(),
        )
        part.tasks.append(task)
        return [task]

    runtime.window.core.ctx.record_tool_calls.side_effect = record_tool_calls
    return runtime, main


def test_agents_v2_runtime_tool_value_conversion_is_persistence_safe():
    assert json_safe_tool_value('{"x": 1}') == {"x": 1}
    assert json_safe_tool_value("plain") == "plain"
    assert json_safe_tool_value(None) == {}
    assert json_safe_tool_result('[1, 2]') == [1, 2]
    assert json_safe_tool_result("") == ""


def test_agents_v2_runtime_local_tool_call_unwraps_params_and_attaches_response():
    runtime, _main = make_runtime(True)

    call_id = runtime.tool_history.record_local_call(
        "read_file", {"params": {"path": "a.txt"}}, actor="w01"
    )
    runtime.tool_history.record_local_result(
        call_id, "read_file", '{"content":"ok"}', actor="w01"
    )

    assert call_id == "agents_v2_run123_1"
    assert runtime.tool_history.calls == [{
        "id": call_id,
        "call_id": call_id,
        "type": "function",
        "function": {"name": "read_file", "arguments": {"path": "a.txt"}},
        "agents_v2_actor": "w01",
        "agents_v2_response": {"content": "ok"},
    }]


def test_agents_v2_runtime_normal_tool_events_pair_by_provider_call_id():
    runtime, _main = make_runtime(True)

    runtime.tool_history.record_call({
        "tool_name": "query_index",
        "tool_kwargs": {"query": "first"},
        "tool_id": "call-a",
    }, actor="orchestrator")
    runtime.tool_history.record_call({
        "tool_name": "query_index",
        "tool_kwargs": {"query": "second"},
        "tool_id": "call-b",
    }, actor="orchestrator")
    runtime.tool_history.record_result({
        "tool_name": "query_index",
        "tool_output": {"content": "B"},
        "tool_id": "call-b",
    }, actor="orchestrator")
    runtime.tool_history.record_result({
        "tool_name": "query_index",
        "tool_output": {"content": "A"},
        "tool_id": "call-a",
    }, actor="orchestrator")

    assert [item["agents_v2_response"] for item in runtime.tool_history.calls] == ["A", "B"]


def test_agents_v2_runtime_result_without_call_id_matches_oldest_unanswered_same_tool():
    runtime, _main = make_runtime(True)
    # Use a normal persisted tool here. ``search`` belongs to the Mouse & Keyboard
    # realtime-only hidden tool set and is intentionally excluded from durable/UI
    # tool history.
    runtime.tool_history.record_call({"tool_name": "query_index", "tool_kwargs": {"q": 1}}, actor="w01")
    runtime.tool_history.record_call({"tool_name": "query_index", "tool_kwargs": {"q": 2}}, actor="w01")

    runtime.tool_history.record_result({"tool_name": "query_index", "tool_output": "one"}, actor="w01")
    runtime.tool_history.record_result({"tool_name": "query_index", "tool_output": "two"}, actor="w01")

    assert [item["agents_v2_response"] for item in runtime.tool_history.calls] == ["one", "two"]


def test_agents_v2_runtime_excludes_orchestration_and_registered_local_tools_from_event_capture():
    runtime, _main = make_runtime(True)
    runtime.tool_history.register_plugin("save_file")

    runtime.tool_history.record_call({"tool_name": "agent_create", "tool_kwargs": {}}, actor="orchestrator")
    runtime.tool_history.record_call({"tool_name": "save_file", "tool_kwargs": {"path": "x"}}, actor="w01")
    runtime.tool_history.record_call({"tool_name": "query_index", "tool_kwargs": {"query": "x"}}, actor="w01")

    assert [item["function"]["name"] for item in runtime.tool_history.calls] == ["query_index"]


def test_agents_v2_runtime_export_tool_chain_replaces_previous_display_chain():
    runtime, main = make_runtime(True, {
        "tool_calls": [{"id": "old"}],
        "agents_v2_tool_calls_display": True,
        "other": 7,
    })
    runtime.tool_history.calls = [{"id": "new", "function": {"name": "search", "arguments": {}}}]

    runtime.tool_history.export()

    assert main.extra["tool_calls"] == runtime.tool_history.calls
    assert main.extra["agents_v2_tool_calls_display"] is True
    assert main.extra["other"] == 7
    runtime.window.core.ctx.update_item.assert_called_once_with(main)


def test_agents_v2_runtime_export_disabled_removes_only_agents_v2_owned_chain():
    runtime, main = make_runtime(False, {
        "tool_calls": [{"id": "old"}],
        "agents_v2_tool_calls_display": True,
        "other": "keep",
    })

    runtime.tool_history.export()

    assert main.extra == {"other": "keep"}
    runtime.window.core.ctx.update_item.assert_called_once_with(main)


def test_agents_v2_runtime_export_disabled_preserves_foreign_tool_data():
    foreign = [{"id": "foreign"}]
    runtime, main = make_runtime(False, {"tool_calls": foreign, "other": 1})

    runtime.tool_history.export()

    assert main.extra["tool_calls"] is foreign
    runtime.window.core.ctx.update_item.assert_not_called()


def test_agents_v2_runtime_empty_new_chain_clears_previous_agents_v2_display():
    runtime, main = make_runtime(True, {
        "tool_calls": [{"id": "old"}],
        "agents_v2_tool_calls_display": True,
    })

    runtime.tool_history.export()

    assert "tool_calls" not in main.extra
    assert "agents_v2_tool_calls_display" not in main.extra
    runtime.window.core.ctx.update_item.assert_called_once_with(main)


def test_custom_agent_session_status_supports_shared_tool_persistence():
    from pygpt_net.core.agents.runners.session_components import SessionStatus
    runtime, main = make_runtime()
    runtime.status = SessionStatus(runtime)
    call_id = runtime.tool_history.persist_call('read_file', {'path': 'a.txt'}, 'orchestrator')
    assert runtime.tool_history.persist_result('file content', 'orchestrator', 'read_file', call_id)
    task = main.parts[0].tasks[0]
    assert task.tool_output == 'file content'
    assert task.extra['status'] == 'completed'


def test_agents_v2_shared_tool_persistence_still_refreshes_status():
    runtime, _main = make_runtime()
    runtime.status = SimpleNamespace(refresh_tools=MagicMock())
    call_id = runtime.tool_history.persist_call('read_file', {'path': 'a.txt'}, 'orchestrator')
    assert runtime.tool_history.persist_result('file content', 'orchestrator', 'read_file', call_id)
    assert runtime.status.refresh_tools.call_count == 2
    runtime.status.refresh_tools.assert_called_with('orchestrator')


def test_hidden_computer_call_notifies_ui_without_persisting_tools():
    runtime, main = make_runtime()
    runtime.emitter = MagicMock()
    result = runtime.tool_history.persist_call('mouse_click', {'x': 10, 'y': 20}, 'orchestrator')
    assert result
    runtime.emitter.computer_use.assert_called_once_with(True)
    runtime.window.core.ctx.record_tool_calls.assert_not_called()
    assert main.parts[0].tasks == []


def test_hidden_worker_computer_call_signals_global_badge_without_renderer():
    runtime, _ = make_runtime()
    runtime.visible = False
    runtime.emitter = MagicMock()
    runtime.tool_history.persist_call('mouse_click', {'x': 1, 'y': 2}, 'w01')
    runtime.window.computer_use_badge.active_changed.emit.assert_called_once_with(True)
    runtime.emitter.computer_use.assert_not_called()
    runtime.window.core.ctx.record_tool_calls.assert_not_called()
