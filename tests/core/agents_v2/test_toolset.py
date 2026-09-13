#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pygpt_net.core.agents_v2.toolset as toolset_module
from pygpt_net.core.agents_v2.strategy import AgentToolSurface
from pygpt_net.core.agents_v2.toolset import RuntimeToolset


class FakeFunctionTool:
    @classmethod
    def from_defaults(cls, async_fn=None, name=None, description=None, **kwargs):
        return SimpleNamespace(
            async_fn=async_fn,
            metadata=SimpleNamespace(name=name, description=description),
            kwargs=kwargs,
        )


def make_runtime():
    runtime = SimpleNamespace(
        primary_actor="primary",
        orchestrator_actor="orchestrator",
        tool_factory=MagicMock(),
        delegate_task=AsyncMock(),
        create_worker=AsyncMock(),
        update_worker=AsyncMock(),
        start_worker=AsyncMock(),
        worker_status=AsyncMock(),
        worker_list=AsyncMock(),
        wait_workers=AsyncMock(),
        stop_worker=AsyncMock(),
        remove_worker=AsyncMock(),
        set_status=AsyncMock(),
        request_workflow_finish=AsyncMock(),
        finish_workflow=AsyncMock(),
        swarm_status=AsyncMock(),
        start_swarm=AsyncMock(),
    )
    runtime.tool_factory.build_orchestrator.side_effect = lambda actor: [
        SimpleNamespace(metadata=SimpleNamespace(name=f"local:{actor}"))
    ]
    return runtime


def names(tools):
    return [tool.metadata.name for tool in tools]


def test_primary_agent_tools_expose_normal_tools_and_single_delegate_bridge(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()

    tools = RuntimeToolset(runtime).primary_agent_tools()

    assert names(tools) == ["local:primary", "delegate_task"]
    assert tools[-1].async_fn is runtime.delegate_task
    runtime.tool_factory.build_orchestrator.assert_called_once_with("primary")


def test_orchestrator_tools_expose_worker_lifecycle_then_normal_tools(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()

    tools = RuntimeToolset(runtime).orchestrator_tools()

    assert names(tools) == [
        "agent_create", "agent_update", "agent_run", "agent_status", "agent_list",
        "agent_wait", "agent_stop", "agent_remove", "workflow_status", "workflow_finish",
        "local:orchestrator",
    ]
    assert tools[-2].async_fn is runtime.request_workflow_finish
    runtime.tool_factory.build_orchestrator.assert_called_once_with("orchestrator")


def test_swarm_tools_prepend_swarm_contract_to_orchestrator_surface(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()
    runtime.orchestrator_tools = lambda: RuntimeToolset(runtime).orchestrator_tools()

    tools = RuntimeToolset(runtime).swarm_tools()

    assert names(tools)[:4] == ["swarm_start", "swarm_status", "agent_create", "agent_update"]
    assert names(tools)[-1] == "local:orchestrator"


def test_main_agent_tools_dispatch_by_strategy_surface(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()
    toolset = RuntimeToolset(runtime)
    runtime.primary_agent_tools = MagicMock(return_value=["primary"])
    runtime.orchestrator_tools = MagicMock(return_value=["orchestrator"])
    runtime.swarm_tools = MagicMock(return_value=["swarm"])

    for surface, expected in [
        (AgentToolSurface.PRIMARY, ["primary"]),
        (AgentToolSurface.ORCHESTRATOR, ["orchestrator"]),
        (AgentToolSurface.SWARM, ["swarm"]),
    ]:
        runtime.strategy = SimpleNamespace(tool_surface=surface)
        assert toolset.main_agent_tools() == expected
