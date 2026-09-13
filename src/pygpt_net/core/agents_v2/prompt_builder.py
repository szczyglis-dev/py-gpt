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

from typing import Optional

from .prompts import ORCHESTRATOR_BASE_PROMPT, PRIMARY_AGENT_BASE_PROMPT, SWARM_BASE_PROMPT


class RuntimePromptBuilder:
    """Compose role prompts around shared runtime capabilities and context."""

    def __init__(self, runtime):
        self.runtime = runtime

    def compose_agent_system_prompt(
            self,
            base_prompt: str = "",
            additional_system_prompt: Optional[str] = None,
    ) -> str:
        """Compose the shared Agents v2 runtime envelope around an actor prompt.

        Top-level Chat with Agents actors add their role prompt as ``base_prompt``.
        Other integrations (for example Experts) can reuse the same provider/tool/RAG
        runtime context without inheriting the Primary Agent/Orchestrator role.
        """
        if additional_system_prompt is None:
            # ``context.system_prompt`` is already the final PyGPT system prompt after
            # PRE/POST/POST_PROMPT_END processing. Prefer it over preset.prompt so
            # plugin additions are not lost and the base preset is not duplicated.
            additional = str(self.runtime.bridge_system_prompt or "").strip()
            if not additional and self.runtime.preset is not None:
                additional = str(getattr(self.runtime.preset, "prompt", "") or "").strip()
        else:
            additional = str(additional_system_prompt or "").strip()

        capabilities = [
            f"agent_mode={self.runtime.agent_mode.value}",
            f"selected_model={getattr(self.runtime.model, 'id', '')}",
            f"allow_local_tools={self.runtime.allow_local_tools}",
            f"allow_remote_tools={self.runtime.allow_remote_tools}",
            f"rag_index={self.runtime.index_id or 'none'}",
            f"rag_prefetched_context={'yes' if self.runtime.rag_context_text else 'no'}",
            f"shared_attachment_context={'yes' if self.runtime.shared_context_text else 'no'}",
            f"max_parallel_workers={'user_defined_unbounded' if self.runtime.is_swarm_mode else (self.runtime.max_workers_configured or 'unlimited')}",
        ]
        runtime_environment = ""
        if self.runtime.runtime_system_context and self.runtime.runtime_system_context not in additional:
            runtime_environment = (
                "\n\n<runtime_environment>\n"
                + self.runtime.runtime_system_context
                + "\n</runtime_environment>"
            )
        rag_context = self.runtime._rag_prompt_context()
        if rag_context:
            rag_context = "\n\n" + rag_context

        base = str(base_prompt or "").strip()
        prefix = (base + "\n\n") if base else ""
        return (
            prefix
            + "<runtime_capabilities>\n" + "\n".join(capabilities) + "\n</runtime_capabilities>"
            + runtime_environment
            + rag_context
            + "\n\n<additional_system_prompt>\n" + additional + "\n</additional_system_prompt>"
        )

    def _compose_main_agent_prompt(self, base_prompt: str) -> str:
        """Backward-compatible wrapper for top-level Chat with Agents prompts."""
        return self.runtime.compose_agent_system_prompt(base_prompt=base_prompt)

    def primary_agent_prompt(self) -> str:
        return self.runtime.compose_agent_system_prompt(base_prompt=PRIMARY_AGENT_BASE_PROMPT)

    def orchestrator_prompt(self) -> str:
        return self.runtime.compose_agent_system_prompt(base_prompt=ORCHESTRATOR_BASE_PROMPT)

    def swarm_prompt(self) -> str:
        return self.runtime.compose_agent_system_prompt(base_prompt=SWARM_BASE_PROMPT)

    def main_agent_prompt(self) -> str:
        """Return the system prompt declared by the selected runtime strategy."""
        return self.runtime.compose_agent_system_prompt(
            base_prompt=self.runtime.strategy.main_prompt,
        )
