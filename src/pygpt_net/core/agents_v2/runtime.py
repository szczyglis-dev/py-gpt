#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.17 17:42:00                  #
# ================================================== #

from __future__ import annotations

import sys
from .contracts import RuntimeInput, RuntimeOutput
from .mode import AgentMode
from .setup import RuntimeSetup
from .state import WorkerState
from .utils import effective_iteration_limit


class AgentsV2Runtime:
    """State and domain components for one isolated Agents v2 user turn.

    Shared turn state stays here; domain behavior lives in explicit
    collaborators for timeline, tool history, context, status, artifacts, worker
    lifecycle, tool surfaces and prompt composition.
    """

    MAX_WORKERS_DEFAULT = 16

    # Code-level switch only (not exposed in presets/UI). Swarm mode always
    # prefixes worker statuses with the numbered agent identity; other modes use
    # this fallback switch.
    SHOW_AGENT_NAME_IN_STATUS = False

    # Automatic aggregate Swarm status cadence. Individual worker updates may
    # trigger an earlier aggregate refresh, but the reporter never emits more
    # often than this interval unless explicitly requested through swarm_status.
    SWARM_STATUS_INTERVAL = 4.0

    # Keep the aggregate Swarm row readable when single-live-status mode is used.
    # This is a UI-only hold: execution continues and newer statuses are coalesced
    # by RuntimeEmitter until the visibility window expires.
    SWARM_STATUS_MIN_VISIBLE = 2.5

    # Fallback default for the Settings option ``agent.v2.show_tool_chain``.
    # When enabled, normal tool calls made anywhere in the Agents v2 flow are
    # exported to the main conversation CtxItem under ``ctx.extra["tool_calls"]``
    # for durable UI inspection. Orchestration/worker-management plumbing is
    # deliberately excluded.
    RETURN_TOOL_CALLS_TO_MAIN_CTX = False

    # Iteration limits are user-configurable in Settings -> Agents -> Chat with Agents.
    # LlamaIndex treats max_iterations=0 as a falsy value and replaces it with its
    # own default, so PyGPT maps 0 to sys.maxsize to provide the documented
    # "unlimited" behavior while keeping the upstream API contract unchanged.
    MAIN_MAX_ITERATIONS_DEFAULT = 48
    SWARM_MAX_ITERATIONS_DEFAULT = 4096
    WORKER_MAX_ITERATIONS_DEFAULT = 24
    UNLIMITED_MAX_ITERATIONS = sys.maxsize

    # ========================================
    # Lifecycle
    # ========================================

    def __init__(self, window, context, extra, signals, emitter):
        self.window = window
        self.context = context
        self.extra = extra
        self.signals = signals
        self.emitter = emitter

        RuntimeSetup(self).initialize()

    @classmethod
    def from_input(cls, data: RuntimeInput) -> "AgentsV2Runtime":
        """Create a runtime from the stable high-level input contract."""
        return cls(data.window, data.context, data.extra, data.signals, data.emitter)

    def output(self) -> RuntimeOutput:
        """Return a compact snapshot for callers that do not need runtime internals."""
        return RuntimeOutput(
            run_id=self.run_id,
            agent_mode=self.agent_mode,
            finished=bool(self.finished),
            final_answer=str(self.final_answer or ""),
        )

    def is_stopped(self) -> bool:
        return bool(self.window.controller.kernel.stopped())


    # ========================================
    # Configuration
    # ========================================

    @property
    def is_orchestrator_mode(self) -> bool:
        return self.agent_mode == AgentMode.ORCHESTRATOR

    @property
    def is_primary_agent_mode(self) -> bool:
        return self.agent_mode == AgentMode.PRIMARY_AGENT

    @property
    def is_swarm_mode(self) -> bool:
        return self.agent_mode == AgentMode.SWARM

    @property
    def uses_workflow_finish(self) -> bool:
        return self.strategy.uses_workflow_finish

    @property
    def main_max_iterations_configured(self) -> int:
        default = int(getattr(self, self.strategy.main_iterations_default_attr))
        return self._configured_iteration_limit(
            self.strategy.main_iterations_key,
            default,
        )

    @property
    def main_max_iterations(self) -> int:
        return effective_iteration_limit(self.main_max_iterations_configured)

    @property
    def max_workers_configured(self) -> int:
        """Maximum workers for Chat/Orchestrator modes (0 means unlimited)."""
        return self._configured_iteration_limit(
            "agent.v2.max_workers",
            self.MAX_WORKERS_DEFAULT,
        )

    @property
    def worker_max_iterations_configured(self) -> int:
        return self._configured_iteration_limit(
            "agent.v2.worker.max_iterations",
            self.WORKER_MAX_ITERATIONS_DEFAULT,
        )

    @property
    def worker_max_iterations(self) -> int:
        return effective_iteration_limit(self.worker_max_iterations_configured)

    # ========================================
    # Agent identity and diagnostics
    # ========================================

    @property
    def main_agent_name(self) -> str:
        if self.agent_definition is not None:
            return str(self.agent_definition.get("name") or "Custom Agent")
        return self.strategy.main_name

    @property
    def main_agent_description(self) -> str:
        if self.agent_definition is not None:
            return "Custom Agents workflow"
        return self.strategy.main_description

    def main_event(self, suffix: str) -> str:
        return f"{self.strategy.event_prefix} {str(suffix or '').strip()}".strip()


    # ========================================
    # Internal configuration
    # ========================================


    def _configured_iteration_limit(self, key: str, default: int) -> int:
        """Return a validated iteration limit from config (0 means unlimited)."""
        try:
            value = int(self.window.core.config.get(key, default))
        except (TypeError, ValueError):
            value = int(default)
        if value < 0:
            value = 0
        return value
