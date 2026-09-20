import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.agents.custom.runner as runner_module
from pygpt_net.core.agents.custom.runner import DebugConfig, FlowOrchestrator, FlowResult


def test_debug_config_defaults_and_flow_result_fields():
    dbg = DebugConfig()
    assert dbg.log_runtime is True
    assert dbg.log_routes is True
    assert dbg.log_inputs is False
    assert dbg.log_outputs is False
    assert dbg.preview_chars == 280

    ctx = object()
    result = FlowResult(ctx=ctx, final_output="answer", last_response_id="r1")
    assert result.ctx is ctx
    assert result.final_output == "answer"
    assert result.last_response_id == "r1"


def test_extract_text_from_item_supports_string_and_content_parts():
    orchestrator = FlowOrchestrator(window=None)
    assert orchestrator._extract_text_from_item("plain") == "plain"
    assert orchestrator._extract_text_from_item({"content": "text"}) == "text"
    assert orchestrator._extract_text_from_item({
        "content": [{"text": "one"}, {"type": "image"}, {"text": "two"}],
    }) == "one\ntwo"
    assert orchestrator._extract_text_from_item(object()) == ""


def test_build_baton_input_first_agent_uses_initial_messages():
    orchestrator = FlowOrchestrator(window=None)
    graph = SimpleNamespace(agent_to_memory={})
    memory = SimpleNamespace(get=MagicMock())
    messages = [{"id": "server", "role": "user", "content": "question"}]

    prepared, baton, mem_id, mem_state, source = orchestrator._build_baton_input(
        node_id="a",
        g=graph,
        mem=memory,
        initial_messages=messages,
        first_dispatch_done=False,
        last_plain_output="",
        dbg=DebugConfig(),
    )

    assert prepared == [{"role": "user", "content": "question"}]
    assert baton == "question"
    assert mem_id is None
    assert mem_state is None
    assert source == "no-mem:first_initial"


def test_build_baton_input_next_agent_uses_last_plain_output():
    orchestrator = FlowOrchestrator(window=None)
    graph = SimpleNamespace(agent_to_memory={})
    memory = SimpleNamespace(get=MagicMock())

    prepared, baton, _, _, source = orchestrator._build_baton_input(
        node_id="b",
        g=graph,
        mem=memory,
        initial_messages=[{"role": "user", "content": "question"}],
        first_dispatch_done=True,
        last_plain_output="previous answer",
        dbg=DebugConfig(),
    )

    assert prepared == [{"role": "user", "content": "previous answer"}]
    assert baton == "previous answer"
    assert source == "no-mem:last_output"


def test_update_memory_after_step_replaces_last_memory_item_with_baton_pair():
    orchestrator = FlowOrchestrator(window=None)
    state = SimpleNamespace(
        items=[{"role": "system", "content": "keep"}, {"role": "assistant", "content": "old"}],
        set_from=MagicMock(),
    )
    orchestrator._update_memory_after_step(
        node_id="a",
        mem_state=state,
        baton_user_text="question",
        display_text="answer",
        last_response_id="r1",
        dbg=DebugConfig(),
    )
    state.set_from.assert_called_once_with([
        {"role": "system", "content": "keep"},
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": [{"type": "output_text", "text": "answer"}]},
    ], "r1")


def test_run_flow_without_start_or_agents_returns_empty_result(monkeypatch):
    orchestrator = FlowOrchestrator(window=SimpleNamespace())
    schema = SimpleNamespace(ends={}, agents={})
    graph = SimpleNamespace(start_targets=[], pick_default_start_agent=lambda: None)
    monkeypatch.setattr(runner_module, "parse_schema", lambda value: schema)
    monkeypatch.setattr(runner_module, "build_graph", lambda value: graph)
    monkeypatch.setattr(runner_module, "MemoryManager", lambda: object())
    monkeypatch.setattr(runner_module, "AgentFactory", lambda *args: object())
    ctx = object()
    bridge = SimpleNamespace(stopped=lambda: False)

    result = asyncio.run(orchestrator.run_flow(
        schema=[], messages=[], ctx=ctx, bridge=bridge, agent_kwargs={}, preset=None,
        model=object(), stream=False, use_partial_ctx=False, base_prompt=None,
        system_prompt_extra=None, allow_local_tools_default=False,
        allow_remote_tools_default=False, function_tools=[], trace_id=None,
    ))

    assert result == FlowResult(ctx=ctx, final_output="", last_response_id=None)
