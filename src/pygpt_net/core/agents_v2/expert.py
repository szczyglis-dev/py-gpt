#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 21:45:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
from typing import List

from llama_index.core.base.llms.types import ChatMessage, MessageRole

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.types import MODE_EXPERT, TOOL_EXPERT_CALL_NAME

from .emitter import RuntimeEmitter
from .runtime import AgentsV2Runtime


class _ResponseSignalProxy:
    """Route the one headless runtime event we need through ExpertWorker signals."""

    def __init__(self, expert_signals):
        self.expert_signals = expert_signals

    def emit(self, event):
        self.expert_signals.event.emit(event)


class _RuntimeSignalsProxy:
    def __init__(self, expert_signals):
        self.response = _ResponseSignalProxy(expert_signals)


class _ExpertEmitter(RuntimeEmitter):
    """Agents v2 emitter with no live UI/status output for inline experts."""

    def _emit(self, name: str, **data):
        # Local PyGPT tools still have to cross to the Qt thread. All other Agents
        # v2 rendering/status events are deliberately suppressed for expert calls.
        if name == KernelEvent.AGENT_V2_TOOL_EXEC:
            super()._emit(name, **data)

    def show_loading(self):
        pass


class _ExpertRuntime(AgentsV2Runtime):
    """Headless Agents v2 runtime used as the execution backend for Experts."""

    def emit_runtime_status(self, key: str, worker=None, **kwargs):
        pass

    def emit_worker_status(self, worker, text: str):
        pass

    def record_local_plugin_tool_call(self, name, args, actor: str = "orchestrator"):
        # Expert tool history is already represented by the expert's hidden CtxItem
        # turn. Do not create Agents-v2 partial/task rows inside that hidden memory.
        return self._new_tool_call_id()

    def record_local_plugin_tool_result(self, call_id, name, result, actor: str = "orchestrator"):
        pass

    def record_tool_call(self, event, actor: str = "orchestrator"):
        pass

    def record_tool_result(self, event, actor: str = "orchestrator"):
        pass

    def export_tool_calls_to_main_ctx(self):
        pass


class ExpertAgentBridge:
    """Run one Expert preset through the shared Agents v2 agent/tool runtime."""

    def __init__(self, window, signals):
        self.window = window
        self.signals = signals

    @staticmethod
    def compose_system_prompt(preset_prompt: str, system_prompt: str = "") -> str:
        """Compose caller-supplied expert prompt without losing the preset identity."""
        preset_value = str(preset_prompt or "").strip()
        user_value = str(system_prompt or "").strip()
        if not user_value:
            return preset_value
        if not preset_value:
            return user_value
        return (
            user_value
            + "\n\n<additional_user_system_instruction>\n"
            + preset_value
            + "\n</additional_user_system_instruction>"
        )

    def _history(self, context, instruction: str) -> List[ChatMessage]:
        """Project the existing Expert slave-meta turns into LlamaIndex chat history."""
        if not self.window.core.config.get("use_context"):
            return []

        model = context.model
        model_id = getattr(model, "id", "")
        history = list(context.history or [])
        used_tokens = self.window.core.tokens.from_user(instruction or "", "")
        max_tokens = int(self.window.core.config.get("max_total_tokens") or 0)
        try:
            model_ctx = int(self.window.core.models.get_num_ctx(model_id) or 0)
        except Exception:
            model_ctx = int(getattr(model, "ctx", 0) or 0)
        if model_ctx > 0 and (max_tokens <= 0 or max_tokens > model_ctx):
            max_tokens = model_ctx

        items = self.window.core.ctx.get_history(
            history,
            model_id,
            MODE_EXPERT,
            used_tokens,
            max_tokens,
            ignore_first=True,
        )
        messages: List[ChatMessage] = []
        for item in items:
            if getattr(item, "input", None):
                messages.append(ChatMessage(role=MessageRole.USER, content=str(item.input)))
            if getattr(item, "output", None):
                messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=str(item.output)))
        return messages

    def call(self, context, instruction: str) -> str:
        """Synchronously execute an Expert agent in the ExpertWorker thread."""
        return asyncio.run(self._call(context, instruction))

    async def _call(self, context, instruction: str) -> str:
        proxy = _RuntimeSignalsProxy(self.signals)
        emitter = _ExpertEmitter(context, {"agent_v2_mode": "chat"}, proxy)
        runtime = _ExpertRuntime(
            self.window,
            context,
            {"agent_v2_mode": "chat"},
            proxy,
            emitter,
        )
        runtime.return_tool_calls_to_main_ctx = False
        runtime.prefetch_rag_context(instruction)

        llm = runtime.get_llm(stream=False, actor_id="orchestrator")
        tools = runtime.tool_factory.build_orchestrator(
            runtime.primary_actor,
            exclude={TOOL_EXPERT_CALL_NAME},
        )
        preset = context.preset
        name = str(getattr(preset, "name", "") or "Expert")
        description = str(getattr(preset, "description", "") or "Expert agent")
        agent = runtime.build_agent(
            name=name,
            description=description,
            llm=llm,
            system_prompt=runtime.compose_agent_system_prompt(
                additional_system_prompt=str(context.system_prompt or ""),
            ),
            tools=tools,
        )

        try:
            handler = agent.run(
                user_msg=runtime.build_user_message(instruction),
                chat_history=self._history(context, instruction),
                max_iterations=runtime.main_max_iterations,
                early_stopping_method="generate",
            )
            result = await handler
            runtime.collect_llm_artifacts(
                getattr(agent, "llm", None) or llm,
                response=result,
                actor_id="orchestrator",
            )
            return runtime._result_text(result)
        finally:
            await runtime.cleanup()
