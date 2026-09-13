#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.13 15:14:00                  #
# ================================================== #

from __future__ import annotations

from typing import List

from llama_index.core.tools import FunctionTool

from .strategy import AgentToolSurface


class RuntimeToolset:
    """Build the top-level tool surface for the selected Agents v2 strategy."""

    def __init__(self, runtime):
        self.runtime = runtime

    def primary_agent_tools(self) -> List[FunctionTool]:
        """Build the Primary Agent surface: normal tools + one agent-as-tool bridge."""
        tools: List[FunctionTool] = list(
            self.runtime.tool_factory.build_orchestrator(self.runtime.primary_actor)
        )
        tools.append(FunctionTool.from_defaults(
            async_fn=self.runtime.delegate_task,
            name="delegate_task",
            description=(
                "Delegate one substantial, self-contained subtask to an ephemeral specialist agent. "
                "The runtime automatically creates the specialist, runs the task, waits for completion, "
                "returns its final work product/artifacts, and cleans it up. Use this only when separate "
                "specialist focus, independent review, context isolation, or parallelizable work materially "
                "improves the result; use normal tools directly for routine execution. Parameters: task "
                "(required), optional name, instruction, system_prompt and language. language may be omitted "
                "to inherit the current user-language contract."
            ),
        ))
        return tools

    def orchestrator_tools(self) -> List[FunctionTool]:
        """Build the legacy Orchestrator surface with explicit worker lifecycle tools."""
        tools: List[FunctionTool] = [
            FunctionTool.from_defaults(
                async_fn=self.runtime.create_worker,
                name="agent_create",
                description=(
                    "Create a runtime worker. Parameters: name, instruction, language, optional system_prompt, optional task. "
                    "language is REQUIRED and must match the language of the current end-user request. "
                    "When task is provided the worker starts immediately and runs asynchronously."
                ),
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.update_worker,
                name="agent_update",
                description="Update an idle worker's name/role/language/system prompt while preserving its in-memory history.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.start_worker,
                name="agent_run",
                description="Start/reuse an existing idle/completed worker on a new task. Its in-memory history is retained.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.worker_status,
                name="agent_status",
                description="Return one worker's state, latest progress, result, error and produced artifacts as JSON.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.worker_list,
                name="agent_list",
                description="Return all runtime workers and their states as JSON.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.wait_workers,
                name="agent_wait",
                description=(
                    "Wait asynchronously for comma-separated agent_ids, or all workers when empty. "
                    "wait_for is 'all' or 'any'; timeout_seconds is capped at 600."
                ),
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.stop_worker,
                name="agent_stop",
                description="Cooperatively stop/cancel a running worker by ID.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.remove_worker,
                name="agent_remove",
                description="Stop if needed and remove a runtime worker by ID.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.set_status,
                name="workflow_status",
                description="Set/replace the single transient user-visible workflow status line.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.runtime.request_workflow_finish,
                name="workflow_finish",
                description=(
                    "Validate that the whole user task is ready to finalize. Call exactly once with no arguments after "
                    "all required work and verification are complete. After the tool returns, send the complete final "
                    "answer as normal assistant text and do not call any more tools."
                ),
            ),
        ]
        # The Orchestrator remains a full PyGPT actor; delegation is a strategy,
        # not a capability boundary.
        tools.extend(self.runtime.tool_factory.build_orchestrator(self.runtime.orchestrator_actor))
        return tools

    def swarm_tools(self) -> List[FunctionTool]:
        """Build Swarm surface: explicit lifecycle plus swarm declaration/status tools."""
        tools = self.runtime.orchestrator_tools()
        # Insert Swarm-specific controls before the generic lifecycle tools to
        # make the required declaration/status contract prominent to the model.
        tools.insert(0, FunctionTool.from_defaults(
            async_fn=self.runtime.swarm_status,
            name="swarm_status",
            description=(
                "Emit and return an aggregate swarm snapshot: declared/created/running/completed/failed/stopped counts "
                "plus numbered worker activity. Call after launch and at meaningful checkpoints while the swarm runs."
            ),
        ))
        tools.insert(0, FunctionTool.from_defaults(
            async_fn=self.runtime.start_swarm,
            name="swarm_start",
            description=(
                "Declare the exact positive number of workers requested by the user. REQUIRED before any agent_create "
                "call in Swarm mode. There is no fixed global worker cap; the declared user-requested count becomes "
                "the exact size of this swarm for the run."
            ),
        ))
        return tools

    def main_agent_tools(self) -> List[FunctionTool]:
        """Return the tool surface declared by the selected runtime strategy."""
        surface = self.runtime.strategy.tool_surface
        if surface == AgentToolSurface.SWARM:
            return self.runtime.swarm_tools()
        if surface == AgentToolSurface.ORCHESTRATOR:
            return self.runtime.orchestrator_tools()
        return self.runtime.primary_agent_tools()
