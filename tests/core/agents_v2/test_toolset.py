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
        tool_factory=MagicMock(),
        delegation=SimpleNamespace(delegate=AsyncMock()),
        workers=SimpleNamespace(
            communication=SimpleNamespace(tools=MagicMock(return_value=[])),
            create=AsyncMock(),
            update=AsyncMock(),
            start=AsyncMock(),
            status=AsyncMock(),
            list=AsyncMock(),
            wait=AsyncMock(),
            stop=AsyncMock(),
            remove=AsyncMock(),
        ),
        status=SimpleNamespace(update=AsyncMock()),
        workflow=SimpleNamespace(
            request_finish=AsyncMock(),
            finish=AsyncMock(),
            status=AsyncMock(),
            declare_swarm=AsyncMock(),
        ),
    )
    runtime.tool_factory.build_orchestrator.side_effect = lambda actor: [
        SimpleNamespace(metadata=SimpleNamespace(name=f"local:{actor}"))
    ]
    runtime.context = SimpleNamespace(ctx=SimpleNamespace())
    runtime.window = SimpleNamespace(
        core=SimpleNamespace(
            context_manager=SimpleNamespace(build_agent_tools=MagicMock(return_value=[])),
            debug=SimpleNamespace(log=MagicMock()),
        ),
    )
    runtime.tools = RuntimeToolset(runtime)
    return runtime


def names(tools):
    return [tool.metadata.name for tool in tools]


def test_primary_agent_tools_expose_normal_tools_and_single_delegate_bridge(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()

    tools = RuntimeToolset(runtime).primary()

    assert names(tools) == ["local:primary", "delegate_task", "workflow_status"]
    assert tools[-2].async_fn is runtime.delegation.delegate
    assert tools[-1].async_fn is runtime.status.update
    runtime.tool_factory.build_orchestrator.assert_called_once_with("primary")


def test_orchestrator_tools_expose_worker_lifecycle_then_normal_tools(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()

    tools = RuntimeToolset(runtime).orchestrator()

    assert names(tools) == [
        "agent_create", "agent_update", "agent_run", "agent_status", "agent_list",
        "agent_wait", "agent_stop", "agent_remove", "workflow_status", "workflow_finish",
        "local:primary",
    ]
    assert tools[-2].async_fn is runtime.workflow.request_finish
    runtime.tool_factory.build_orchestrator.assert_called_once_with("primary")


def test_swarm_tools_prepend_swarm_contract_to_orchestrator_surface(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()
    runtime.tools.orchestrator = lambda: RuntimeToolset(runtime).orchestrator()

    tools = RuntimeToolset(runtime).swarm()

    assert names(tools)[:4] == ["swarm_start", "swarm_status", "agent_create", "agent_update"]
    assert names(tools)[-1] == "local:primary"


def test_main_agent_tools_dispatch_by_strategy_surface(monkeypatch):
    monkeypatch.setattr(toolset_module, "FunctionTool", FakeFunctionTool)
    runtime = make_runtime()
    toolset = runtime.tools
    runtime.tools.primary = MagicMock(return_value=["primary"])
    runtime.tools.orchestrator = MagicMock(return_value=["orchestrator"])
    runtime.tools.swarm = MagicMock(return_value=["swarm"])

    for surface, expected in [
        (AgentToolSurface.PRIMARY, ["primary"]),
        (AgentToolSurface.ORCHESTRATOR, ["orchestrator"]),
        (AgentToolSurface.SWARM, ["swarm"]),
    ]:
        runtime.strategy = SimpleNamespace(tool_surface=surface)
        assert toolset.main() == expected
