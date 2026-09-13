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

from dataclasses import dataclass
from enum import Enum

from .mode import AgentMode
from .prompts import (
    ORCHESTRATOR_BASE_PROMPT,
    ORCHESTRATOR_WORKER_BASE_PROMPT,
    PRIMARY_AGENT_BASE_PROMPT,
    PRIMARY_AGENT_WORKER_BASE_PROMPT,
    SWARM_BASE_PROMPT,
    SWARM_WORKER_BASE_PROMPT,
)


class AgentToolSurface(str, Enum):
    """Top-level tool policy used by a runtime strategy."""

    PRIMARY = "primary"
    ORCHESTRATOR = "orchestrator"
    SWARM = "swarm"


@dataclass(frozen=True)
class AgentRuntimeStrategy:
    """Declarative behavior that distinguishes one top-level Agents v2 mode."""

    mode: AgentMode
    main_name: str
    main_description: str
    event_prefix: str
    main_prompt: str
    worker_prompt: str
    worker_controller_tag: str
    tool_surface: AgentToolSurface
    uses_workflow_finish: bool
    main_iterations_key: str
    main_iterations_default_attr: str


_STRATEGIES = {
    AgentMode.PRIMARY_AGENT: AgentRuntimeStrategy(
        mode=AgentMode.PRIMARY_AGENT,
        main_name="Primary Agent",
        main_description="Main user-facing agent",
        event_prefix="PRIMARY AGENT",
        main_prompt=PRIMARY_AGENT_BASE_PROMPT,
        worker_prompt=PRIMARY_AGENT_WORKER_BASE_PROMPT,
        worker_controller_tag="primary_agent_system_instruction",
        tool_surface=AgentToolSurface.PRIMARY,
        uses_workflow_finish=False,
        main_iterations_key="agent.v2.max_iterations",
        main_iterations_default_attr="MAIN_MAX_ITERATIONS_DEFAULT",
    ),
    AgentMode.ORCHESTRATOR: AgentRuntimeStrategy(
        mode=AgentMode.ORCHESTRATOR,
        main_name="Orchestrator",
        main_description="Main orchestrator agent",
        event_prefix="ORCHESTRATOR",
        main_prompt=ORCHESTRATOR_BASE_PROMPT,
        worker_prompt=ORCHESTRATOR_WORKER_BASE_PROMPT,
        worker_controller_tag="orchestrator_system_instruction",
        tool_surface=AgentToolSurface.ORCHESTRATOR,
        uses_workflow_finish=True,
        main_iterations_key="agent.v2.max_iterations",
        main_iterations_default_attr="MAIN_MAX_ITERATIONS_DEFAULT",
    ),
    AgentMode.SWARM: AgentRuntimeStrategy(
        mode=AgentMode.SWARM,
        main_name="Swarm Orchestrator",
        main_description="Main swarm orchestrator agent",
        event_prefix="SWARM",
        main_prompt=SWARM_BASE_PROMPT,
        worker_prompt=SWARM_WORKER_BASE_PROMPT,
        worker_controller_tag="swarm_orchestrator_system_instruction",
        tool_surface=AgentToolSurface.SWARM,
        uses_workflow_finish=True,
        main_iterations_key="agent.v2.swarm.max_iterations",
        main_iterations_default_attr="SWARM_MAX_ITERATIONS_DEFAULT",
    ),
}


def get_agent_strategy(mode: AgentMode) -> AgentRuntimeStrategy:
    """Resolve the declarative strategy for an already-coerced AgentMode."""
    return _STRATEGIES[mode]
