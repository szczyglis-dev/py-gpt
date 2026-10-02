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

import asyncio
import uuid
from types import SimpleNamespace


from .artifacts import RuntimeArtifacts
from .context import RuntimeContext
from .delegation import AgentDelegateBridge
from .memory import AgentsV2MemoryStore
from .mode import AGENT_MODE, AGENT_MODE_CONFIG_DEFAULT, AGENT_MODE_CONFIG_KEY
from .prompt_builder import RuntimePromptBuilder
from .prompts import agents_directory_exists
from .status import RuntimeStatus
from .strategy import get_agent_strategy
from .timeline import RuntimeTimeline
from .tools import WorkerToolFactory
from .tool_history import RuntimeToolHistory
from .toolset import RuntimeToolset
from .usage import RuntimeUsage
from .verbose import AgentsV2VerboseLogger
from .workers import WorkerRuntime
from .workflow import WorkflowControl


class RuntimeSetup:
    """Initialize a runtime in dependency order, keeping construction readable."""

    def __init__(self, runtime):
        self.runtime = runtime

    def initialize(self):
        self._components()
        self._selection()
        self._state()
        self._resources()
        self._context()
        self._actor()
        self._diagnostics()

    # ========================================
    # Components
    # ========================================

    def _components(self):
        runtime = self.runtime
        # Runtime owns the shared turn state. Domain work lives in explicit collaborators so
        # execution modes can evolve independently without growing this class.
        runtime.timeline = RuntimeTimeline(runtime)
        runtime.tool_history = RuntimeToolHistory(runtime)
        runtime.inputs = RuntimeContext(runtime)
        runtime.status = RuntimeStatus(runtime)
        runtime.artifacts = RuntimeArtifacts(runtime)
        runtime.usage = RuntimeUsage(runtime)
        runtime.workers = WorkerRuntime(runtime)
        runtime.workflow = WorkflowControl(runtime)
        runtime.tools = RuntimeToolset(runtime)
        runtime.prompts = RuntimePromptBuilder(runtime)

    # ========================================
    # Selection
    # ========================================

    def _selection(self):
        runtime = self.runtime
        context, extra = runtime.context, runtime.extra
        requested_mode = None
        if isinstance(extra, dict):
            requested_mode = extra.get("agent_v2_mode")
        if requested_mode in (None, ""):
            requested_mode = getattr(context, "agent_v2_mode", None)
        if requested_mode in (None, ""):
            requested_mode = runtime.window.core.config.get(
                AGENT_MODE_CONFIG_KEY,
                AGENT_MODE_CONFIG_DEFAULT,
            )
        runtime.agent_id, runtime.agent_mode, runtime.agent_definition = (
            runtime.window.core.agents_v2.editor.resolve_selection(requested_mode or AGENT_MODE)
        )
        runtime.strategy = get_agent_strategy(runtime.agent_mode)
        runtime.model = context.model
        runtime.preset = context.preset

    # ========================================
    # State
    # ========================================

    def _state(self):
        runtime = self.runtime
        window = runtime.window
        runtime.finished = False
        runtime.final_answer = ""
        runtime.run_id = uuid.uuid4().hex[:12]
        runtime.verbose = AgentsV2VerboseLogger(window, runtime.run_id, agent_mode=runtime.agent_mode)

    # ========================================
    # Resources
    # ========================================

    def _resources(self):
        runtime = self.runtime
        window, context = runtime.window, runtime.context
        runtime.return_tool_calls_to_main_ctx = bool(
            runtime.window.core.config.get(
                "agent.v2.show_tool_chain",
                runtime.RETURN_TOOL_CALLS_TO_MAIN_CTX,
            )
        )
        runtime.memory_store = AgentsV2MemoryStore(window)
        runtime.allow_local_tools = bool(getattr(runtime.preset, "agent_v2_allow_local_tools", True))
        runtime.allow_remote_tools = bool(getattr(runtime.preset, "agent_v2_allow_remote_tools", True))
        # Preset selection is synchronized into the shared RAG selector by the
        # presets controller. Runtime reads that selector as the single source of
        # truth so a manual toolbox change after selecting a preset takes effect.
        runtime.index_id = getattr(context, "idx", None)
        if runtime.index_id in ("_", "-"):
            runtime.index_id = None
        runtime.rag_context_text = ""

        # PyGPT plugin/provider API wrappers keep mutable state. Workers themselves run
        # concurrently, but shared side-effecting bridges are serialized per runtime.
        runtime.local_tool_lock = asyncio.Lock()

    # ========================================
    # Context
    # ========================================

    def _context(self):
        runtime = self.runtime
        context = runtime.context
        # Native image input in Agents v2 uses ImageBlock directly, outside the
        # normal LlamaIndex Context.append_images() path. Persist the same image
        # references on the main CtxItem so they survive reload and are rendered
        # with the conversation item just like images sent in Chat/Chat with Files.
        runtime.inputs.persist_images()
        runtime.shared_context_text = runtime.inputs.shared_context()
        runtime.runtime_system_context = runtime.inputs.system_context()
        # Resolve .agents once for this run against the conversation/project that
        # started it. Prompt composition then uses the cached state consistently.
        runtime.agents_directory_exists = agents_directory_exists(
            runtime.window,
            ctx=getattr(runtime.context, "ctx", None),
        )
        # BridgeWorker has already executed POST_PROMPT_END before Agents v2 is
        # started. Consume that final prompt verbatim so every enabled plugin
        # (Real Time, Files I/O, Extra Prompt, Vision, etc.) contributes exactly
        # the same system-prompt additions as it does in Chat.
        runtime.bridge_system_prompt = str(getattr(context, "system_prompt", "") or "").strip()
        # Older builds persisted this runtime-only value. Strip it from the live
        # item so any subsequent context update also removes it from storage.
        main_ctx = getattr(context, "ctx", None)
        if main_ctx is not None and isinstance(getattr(main_ctx, "extra", None), dict):
            main_ctx.extra.pop("agents_v2_filesystem_context", None)
        runtime.tool_factory = WorkerToolFactory(runtime)
        # Primary Agent exposes this bridge as delegate_task(); Orchestrator keeps
        # the explicit worker lifecycle tools. The worker runtime itself is shared.
        runtime.delegation = AgentDelegateBridge(runtime)
        runtime.artifacts.seed()

    # ========================================
    # Actor
    # ========================================

    def _actor(self):
        runtime = self.runtime
        runtime.primary_actor = SimpleNamespace(
            # Keep the historical actor id for persisted-part/UI compatibility.
            id="orchestrator",
            name=runtime.main_agent_name,
            progress="",
            stop_requested=False,
            tool_ctx=runtime.artifacts.tool_context("orchestrator"),
            artifacts={"files": [], "images": [], "urls": [], "attachments": []},
        )
        # Keep the Primary Agent's tool context private. Local PyGPT plugins set
        # ctx.reply/results as part of the legacy chat tool pipeline; using the
        # user-visible CtxItem here would feed a plugin result back through
        # KernelEvent.REPLY_RETURN and accidentally start a second Agents v2 run.
        runtime.primary_actor.tool_ctx.set_input(
            str(getattr(runtime.context.ctx, "final_input", None) or runtime.context.prompt or ""),
            "orchestrator",
        )
        runtime.primary_actor.tool_ctx.set_output("", runtime.main_agent_name)

    # ========================================
    # Diagnostics
    # ========================================

    def _diagnostics(self):
        runtime = self.runtime
        runtime.verbose.log("RUNTIME INIT", {
            "agent_mode": runtime.agent_mode.value,
            "agent_id": runtime.agent_id,
            "agent_name": runtime.main_agent_name,
            "model": getattr(runtime.model, "id", None),
            "provider": getattr(runtime.model, "provider", None) if runtime.model is not None else None,
            "preset": getattr(runtime.preset, "name", None) or getattr(runtime.preset, "id", None),
            "allow_local_tools": runtime.allow_local_tools,
            "allow_remote_tools": runtime.allow_remote_tools,
            "show_tool_chain": runtime.return_tool_calls_to_main_ctx,
            "index_id": runtime.index_id,
            "shared_context": runtime.shared_context_text,
            "runtime_system_context": runtime.runtime_system_context,
            "bridge_system_prompt": runtime.bridge_system_prompt,
            "max_workers": (
                "user_defined" if runtime.is_swarm_mode
                else (runtime.max_workers_configured or "unlimited")
            ),
            "main_max_iterations": runtime.main_max_iterations_configured or "unlimited",
            "worker_max_iterations": runtime.worker_max_iterations_configured or "unlimited",
        })

