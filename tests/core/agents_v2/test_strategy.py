#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pygpt_net.core.agents_v2.mode import (
    AGENT_MODE,
    AGENT_MODE_CONFIG_DEFAULT,
    AGENT_MODE_CONFIG_KEY,
    AgentMode,
)
from pygpt_net.core.agents_v2.strategy import AgentToolSurface, get_agent_strategy


def test_agent_mode_coerce_accepts_config_values_and_aliases():
    assert AgentMode.coerce("chat") is AgentMode.PRIMARY_AGENT
    assert AgentMode.coerce("primary") is AgentMode.PRIMARY_AGENT
    assert AgentMode.coerce("primary-agent") is AgentMode.PRIMARY_AGENT
    assert AgentMode.coerce("orchestrator") is AgentMode.ORCHESTRATOR
    assert AgentMode.coerce("swarm_mode") is AgentMode.SWARM
    assert AgentMode.coerce(AgentMode.SWARM) is AgentMode.SWARM


def test_agent_mode_coerce_falls_back_to_primary_agent():
    assert AGENT_MODE is AgentMode.PRIMARY_AGENT
    assert AGENT_MODE_CONFIG_KEY == "agent.v2.mode"
    assert AGENT_MODE_CONFIG_DEFAULT == "chat"
    assert AgentMode.coerce("") is AGENT_MODE
    assert AgentMode.coerce("unknown") is AGENT_MODE


def test_agent_strategies_define_distinct_prompts_tools_and_finish_policy():
    primary = get_agent_strategy(AgentMode.PRIMARY_AGENT)
    orchestrator = get_agent_strategy(AgentMode.ORCHESTRATOR)
    swarm = get_agent_strategy(AgentMode.SWARM)

    assert primary.tool_surface is AgentToolSurface.PRIMARY
    assert primary.uses_workflow_finish is False
    assert primary.main_name == "Primary Agent"
    assert primary.main_prompt != orchestrator.main_prompt

    assert orchestrator.tool_surface is AgentToolSurface.ORCHESTRATOR
    assert orchestrator.uses_workflow_finish is True
    assert orchestrator.worker_controller_tag == "orchestrator_system_instruction"

    assert swarm.tool_surface is AgentToolSurface.SWARM
    assert swarm.uses_workflow_finish is True
    assert swarm.main_iterations_key == "agent.v2.swarm.max_iterations"
    assert swarm.worker_controller_tag == "swarm_orchestrator_system_instruction"
