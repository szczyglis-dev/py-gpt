#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.16 10:57:00                  #
# ================================================== #

from __future__ import annotations

from typing import Optional

from .prompts import (
    CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY,
    CUSTOM_PRIMARY_PROMPT_CONFIG_KEY,
    CUSTOM_STEP_BY_STEP_PROMPT_CONFIG_KEY,
    CUSTOM_SWARM_PROMPT_CONFIG_KEY,
    ORCHESTRATOR_BASE_PROMPT,
    PRIMARY_AGENT_BASE_PROMPT,
    SWARM_BASE_PROMPT,
    build_custom_main_prompt,
    resolve_step_by_step_prompt,
)


class RuntimePromptBuilder:
    """Compose role prompts around shared runtime capabilities and context."""

    def __init__(self, runtime):
        self.runtime = runtime

    def compose_agent_system_prompt(
            self,
            base_prompt: str = "",
            additional_system_prompt: Optional[str] = None,
            include_project_rules: bool = False,
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

        project_rules = ""
        if include_project_rules:
            if not bool(getattr(self.runtime, "project_rules_loaded", False)):
                self.runtime.project_rules_text = self.runtime.context_api.load_project_rules()
                self.runtime.project_rules_loaded = True
            rules = str(getattr(self.runtime, "project_rules_text", "") or "").strip()
            if rules:
                project_rules = (
                    "\n\n<additional_project_rules source=\"%workdir%/AGENTS.md\">\n"
                    "The following project-specific rules apply to the main agent for this "
                    "workdir. Follow them in addition to the other system instructions.\n"
                    + rules
                    + "\n</additional_project_rules>"
                )

        step_by_step_rules = str(
            self.runtime.window.core.config.get(
                CUSTOM_STEP_BY_STEP_PROMPT_CONFIG_KEY,
                "",
            ) or ""
        ).strip()
        base = resolve_step_by_step_prompt(
            base_prompt,
            bool(getattr(self.runtime, "step_by_step_enabled", False)),
            step_by_step_rules,
        ).strip()
        prefix = (base + "\n\n") if base else ""
        return (
            prefix
            + "<runtime_capabilities>\n" + "\n".join(capabilities) + "\n</runtime_capabilities>"
            + runtime_environment
            + rag_context
            + "\n\n<additional_system_prompt>\n" + additional + "\n</additional_system_prompt>"
            + project_rules
        )

    def _compose_main_agent_prompt(self, base_prompt: str) -> str:
        """Backward-compatible wrapper for top-level Chat with Agents prompts."""
        return self.compose_agent_system_prompt(
            base_prompt=base_prompt,
            include_project_rules=True,
        )

    def _configured_main_prompt(self, default_prompt: str, config_key: str) -> str:
        """Return a custom role prompt when configured, otherwise the built-in prompt."""
        custom = str(self.runtime.window.core.config.get(config_key, "") or "").strip()
        if custom:
            return build_custom_main_prompt(custom)
        return default_prompt

    def primary_agent_prompt(self) -> str:
        return self.compose_agent_system_prompt(
            base_prompt=self._configured_main_prompt(
                PRIMARY_AGENT_BASE_PROMPT,
                CUSTOM_PRIMARY_PROMPT_CONFIG_KEY,
            ),
            include_project_rules=True,
        )

    def orchestrator_prompt(self) -> str:
        return self.compose_agent_system_prompt(
            base_prompt=self._configured_main_prompt(
                ORCHESTRATOR_BASE_PROMPT,
                CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY,
            ),
            include_project_rules=True,
        )

    def swarm_prompt(self) -> str:
        return self.compose_agent_system_prompt(
            base_prompt=self._configured_main_prompt(
                SWARM_BASE_PROMPT,
                CUSTOM_SWARM_PROMPT_CONFIG_KEY,
            ),
            include_project_rules=True,
        )

    def main_agent_prompt(self) -> str:
        """Return the configured system prompt for the selected runtime strategy."""
        mode = str(getattr(self.runtime.agent_mode, "value", "") or "")
        if mode == "primary_agent":
            return self.primary_agent_prompt()
        if mode == "orchestrator":
            return self.orchestrator_prompt()
        if mode == "swarm":
            return self.swarm_prompt()
        return self.compose_agent_system_prompt(
            base_prompt=self.runtime.strategy.main_prompt,
            include_project_rules=True,
        )
