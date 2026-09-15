#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.15 15:00:00                  #
# ================================================== #

from types import SimpleNamespace

from .context import RuntimeContext
from .memory import AgentsV2MemoryStore
from .mode import AGENT_MODE_CONFIG_DEFAULT, AGENT_MODE_CONFIG_KEY, AgentMode
from .prompt_builder import RuntimePromptBuilder
from .runner import Runner
from .strategy import get_agent_strategy


class _PromptPreviewRuntime:
    """Lightweight, side-effect-free runtime view used by the live token counter.

    It intentionally reuses RuntimePromptBuilder/RuntimeContext instead of copying
    Agents v2 prompt composition into core.tokens. No agent, LLM, memory or tool
    runtime is created.
    """

    MAX_WORKERS_DEFAULT = 16

    def __init__(
            self,
            window,
            model,
            preset,
            ctx,
            attachments,
            index_id,
            bridge_system_prompt: str,
    ):
        self.window = window
        self.model = model
        self.preset = preset
        self.context = SimpleNamespace(
            ctx=ctx,
            attachments=attachments or {},
            idx=index_id,
        )
        self.agent_mode = AgentMode.coerce(
            window.core.config.get(AGENT_MODE_CONFIG_KEY, AGENT_MODE_CONFIG_DEFAULT)
        )
        self.strategy = get_agent_strategy(self.agent_mode)
        self.allow_local_tools = bool(
            getattr(preset, "agent_v2_allow_local_tools", True)
        )
        self.allow_remote_tools = bool(
            getattr(preset, "agent_v2_allow_remote_tools", True)
        )
        self.index_id = (
            (getattr(preset, "idx", None) if preset is not None else None)
            or index_id
        )
        if self.index_id == "_":
            self.index_id = None

        # Preflight happens before the user turn starts, so retrieval has not run
        # yet. The normal <rag_access> envelope is still composed when an index is
        # selected; only request-specific retrieved text is absent at this point.
        self.rag_context_text = ""
        self.step_by_step_enabled = bool(
            window.core.config.get("agent.v2.step_by_step", False)
        )
        self.bridge_system_prompt = str(bridge_system_prompt or "").strip()
        self.project_rules_text = ""
        self.project_rules_loaded = False

        self.context_api = RuntimeContext(self)
        self.shared_context_text = self.context_api._build_shared_context()
        self.runtime_system_context = self.context_api._build_runtime_system_context()
        self.prompt_api = RuntimePromptBuilder(self)

    @property
    def is_swarm_mode(self) -> bool:
        return self.agent_mode == AgentMode.SWARM

    @property
    def max_workers_configured(self) -> int:
        try:
            value = int(
                self.window.core.config.get(
                    "agent.v2.max_workers",
                    self.MAX_WORKERS_DEFAULT,
                )
            )
        except (TypeError, ValueError):
            value = self.MAX_WORKERS_DEFAULT
        return max(0, value)

    def verbose_log(self, *args, **kwargs):
        # Live token updates must not produce Agents v2 workflow/debug entries.
        return None

    def verbose_text(self, *args, **kwargs):
        return None

    def has_rag_index(self) -> bool:
        return self.context_api.has_rag_index()

    def _rag_prompt_context(self) -> str:
        return self.context_api._rag_prompt_context()

    def main_agent_prompt(self) -> str:
        return self.prompt_api.main_agent_prompt()


class AgentsV2:
    def __init__(self, window=None):
        self.window = window
        self.runner = Runner(window)
        # Stateless helper shared by the live UI token estimator. Runtime turns
        # may still instantiate/use their own facade; both read the same hidden
        # DB-backed Primary Agent memory.
        self.memory_store = AgentsV2MemoryStore(window)

    def build_main_system_prompt_preview(
            self,
            system_prompt: str,
            model,
            current_ctx=None,
    ) -> str:
        """Compose the main Agents v2 system prompt for preflight token count.

        This runs before any user input is dispatched. It deliberately creates no
        AgentsV2Runtime/agent/LLM; it only feeds the current UI/runtime state into
        the same RuntimePromptBuilder used by the real turn.
        """
        if model is None:
            return str(system_prompt or "")

        preset = self.window.controller.presets.get_current()
        try:
            attachments = dict(self.window.core.attachments.get_all("agent_v2"))
        except Exception:
            attachments = {}
        try:
            index_id = self.window.controller.idx.get_current()
        except Exception:
            index_id = None

        preview = _PromptPreviewRuntime(
            window=self.window,
            model=model,
            preset=preset,
            ctx=current_ctx,
            attachments=attachments,
            index_id=index_id,
            bridge_system_prompt=system_prompt,
        )
        return preview.main_agent_prompt()

    def count_current_history_tokens(
            self,
            model,
            used_tokens: int = 0,
            max_tokens: int = 0,
    ):
        """Return token usage for the history actually replayed by Agents v2."""
        if model is None:
            return 0, 0
        core_ctx = self.window.core.ctx
        master_ctx = core_ctx.get_last_item()
        if master_ctx is None:
            items = core_ctx.get_items()
            if items:
                master_ctx = items[-1]
        if master_ctx is None or master_ctx.meta is None:
            return 0, 0
        preset = self.window.controller.presets.get_current()
        return self.memory_store.count_history_tokens(
            master_ctx,
            preset,
            model,
            used_tokens=used_tokens,
            max_tokens=max_tokens,
        )
