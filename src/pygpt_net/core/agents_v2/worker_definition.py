#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.17 15:58:00                  #
# ================================================== #

from __future__ import annotations

from llama_index.core.memory import Memory
from .state import WorkerState


class WorkerDefinition:
    """Build and update specialist agents; updates preserve their working memory."""

    def __init__(self, runtime, communication):
        self.runtime = runtime
        self.communication = communication

    # ========================================
    # Agent definitions
    # ========================================

    def create(self, name, instruction, language, system_prompt):
        wid = self.runtime.workers.next_id()
        swarm_number = self.runtime.workers.created_count + 1 if self.runtime.is_swarm_mode else 0
        name = self.runtime.status.worker_name(name, swarm_number) if self.runtime.is_swarm_mode else name
        state = WorkerState(
            id=wid,
            name=name,
            instruction=instruction,
            language=language[:80],
            system_prompt=system_prompt or "",
            agent=None,
            memory=None,
            tool_ctx=self.runtime.artifacts.worker_context(wid),
        )
        llm = self.runtime.inputs.llm(stream=False, actor_id=wid)
        worker_prompt = self._prompt(
            name, instruction, state.language, system_prompt or ""
        )
        worker_tools = self.runtime.tool_factory.build(state)
        if self.runtime.window.core.context_manager.enabled():
            state.memory = self.runtime.window.core.context_manager.build_agent_memory(
                self.runtime,
                actor_id=wid,
                system_prompt=worker_prompt,
                tools=worker_tools,
                persistent=False,
            )
        else:
            state.memory = Memory.from_defaults(
                session_id=f"agents_v2_{self.runtime.run_id}_{wid}",
                token_limit=self.runtime.inputs.memory_limit(),
            )
        state.agent = self.runtime.inputs.agent(
            name=name,
            description=instruction[:512],
            llm=llm,
            system_prompt=worker_prompt,
            tools=worker_tools,
        )
        if self.runtime.is_swarm_mode:
            state.agent.set_message_receiver(lambda: self.communication.receive(wid))
        return state, swarm_number

    def update(self, state, name, instruction, language, system_prompt):
        if name is not None and name.strip():
            requested_name = name.strip()[:80]
            if self.runtime.is_swarm_mode:
                state.name = self.runtime.status.worker_name(
                    requested_name,
                    self.runtime.workers.number(state.id),
                )
            else:
                state.name = requested_name
        if instruction is not None and instruction.strip():
            state.instruction = instruction.strip()
        if language is not None and language.strip():
            state.language = language.strip()[:80]
        if system_prompt is not None:
            state.system_prompt = system_prompt.strip()

        # Rebuild the agent definition while deliberately preserving Memory.
        llm = self.runtime.inputs.llm(stream=False, actor_id=state.id)
        state.agent = self.runtime.inputs.agent(
            name=state.name,
            description=state.instruction[:512],
            llm=llm,
            system_prompt=self._prompt(state.name, state.instruction, state.language, state.system_prompt),
            tools=self.runtime.tool_factory.build(state),
        )
        if self.runtime.is_swarm_mode:
            state.agent.set_message_receiver(lambda: self.communication.receive(state.id))

    # ========================================
    # Prompts
    # ========================================

    def _prompt(self, name: str, instruction: str, language: str, system_prompt: str) -> str:
        bridge_prompt = str(self.runtime.bridge_system_prompt or "").strip()
        runtime_context = str(self.runtime.runtime_system_context or "").strip()
        # Files I/O historically published a separate Agents-v2 runtime context.
        # Keep that fallback for compatibility, but do not duplicate it now that
        # the final Bridge system prompt is consumed directly.
        runtime_block = ""
        if runtime_context and runtime_context not in bridge_prompt:
            runtime_block = f"<runtime_environment>\n{runtime_context}\n</runtime_environment>"
        worker_base_prompt = self.runtime.strategy.worker_prompt
        controller_tag = self.runtime.strategy.worker_controller_tag
        skills_context = ""
        try:
            skills_context = str(self.runtime.window.core.skills.prompt_catalog() or "").strip()
        except Exception as exc:
            self.runtime.window.core.debug.log(exc)
        return "\n\n".join(filter(None, [
            worker_base_prompt,
            f"<workflow_language>\n{language}\n</workflow_language>",
            f"<worker_identity>\nname={name}\nrole_instruction={instruction}\n</worker_identity>",
            (
                f"<additional_system_prompt>\n{bridge_prompt}\n</additional_system_prompt>"
                if bridge_prompt else ""
            ),
            runtime_block,
            self.runtime.inputs.rag_prompt(),
            skills_context,
            (
                f"<{controller_tag}>\n{system_prompt}\n</{controller_tag}>"
                if system_prompt else ""
            ),
        ])).strip()

