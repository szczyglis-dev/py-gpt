#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.17 14:20:00                  #
# ================================================== #

from __future__ import annotations

from typing import Optional

from .prompts import (
    CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY,
    CUSTOM_PRIMARY_PROMPT_CONFIG_KEY,
    CUSTOM_SWARM_PROMPT_CONFIG_KEY,
    ORCHESTRATOR_BASE_PROMPT,
    PRIMARY_AGENT_BASE_PROMPT,
    SWARM_BASE_PROMPT,
    WORKFLOW_PROGRESS_POLICY,
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
            inject_workflow_policy: bool = True,
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
            f"agent_profile={getattr(self.runtime, 'agent_id', self.runtime.agent_mode.value)}",
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

        base = str(base_prompt or "").strip()
        prefix = (base + "\n\n") if base else ""
        workflow_policy = ""
        if inject_workflow_policy:
            workflow_policy = (
                "\n\n<workflow_progress_policy>\n"
                + WORKFLOW_PROGRESS_POLICY
                + "\n</workflow_progress_policy>"
            )
        return (
            prefix
            + "<runtime_capabilities>\n" + "\n".join(capabilities) + "\n</runtime_capabilities>"
            + workflow_policy
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

    def _custom_main_prompt(self, config_key: str) -> str:
        """Return the user override exactly as configured."""
        return str(self.runtime.window.core.config.get(config_key, "") or "").strip()

    def _configured_main_prompt(self, default_prompt: str, config_key: str) -> str:
        """Return a user override when configured, otherwise the built-in prompt."""
        return self._custom_main_prompt(config_key) or default_prompt

    def _builtin_or_custom_prompt(self, default_prompt: str, config_key: str) -> str:
        """Compose one built-in slot, suppressing built-in policies for an explicit user override."""
        custom = self._custom_main_prompt(config_key)
        return self.compose_agent_system_prompt(
            base_prompt=custom or default_prompt,
            include_project_rules=True,
            inject_workflow_policy=not bool(custom),
        )

    def primary_agent_prompt(self) -> str:
        return self._builtin_or_custom_prompt(
            PRIMARY_AGENT_BASE_PROMPT,
            CUSTOM_PRIMARY_PROMPT_CONFIG_KEY,
        )

    def orchestrator_prompt(self) -> str:
        return self._builtin_or_custom_prompt(
            ORCHESTRATOR_BASE_PROMPT,
            CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY,
        )

    def swarm_prompt(self) -> str:
        return self._builtin_or_custom_prompt(
            SWARM_BASE_PROMPT,
            CUSTOM_SWARM_PROMPT_CONFIG_KEY,
        )

    def main_agent_prompt(self) -> str:
        """Return the configured system prompt for the selected agent profile."""
        custom = getattr(self.runtime, "agent_definition", None)
        if custom is not None:
            base = str(custom.get("system_prompt") or "").strip()
            return self.compose_agent_system_prompt(
                base_prompt=base,
                include_project_rules=True,
                inject_workflow_policy=False,
            )

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
