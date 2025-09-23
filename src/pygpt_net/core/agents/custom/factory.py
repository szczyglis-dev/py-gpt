#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agents import Agent as OpenAIAgent
from pygpt_net.item.preset import PresetItem
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.provider.api.openai.agents.remote_tools import append_tools
from pygpt_net.provider.api.openai.agents.experts import get_experts

from .schema import AgentNode
from .router import build_router_instruction
from .utils import NodeRuntime


@dataclass
class BuiltAgent:
    instance: OpenAIAgent
    name: str
    instructions: str
    multi_output: bool
    allowed_routes: List[str]


class AgentFactory:
    """
    Builds OpenAIAgent instances from AgentNode + NodeRuntime.
    """
    def __init__(self, window, logger) -> None:
        self.window = window
        self.logger = logger

    def build(
        self,
        node: AgentNode,
        node_runtime: NodeRuntime,
        preset: Optional[PresetItem],
        function_tools: List[dict],
        force_router: bool,
        friendly_map: Dict[str, str],
        handoffs_enabled: bool = True,
        context: Optional[BridgeContext] = None,
    ) -> BuiltAgent:
        # Agent name
        agent_name = (node.name or "").strip() or (preset.name if preset else f"Agent {node.id}")

        # Multi-output routing instruction injection
        multi_output = force_router or (len(node.outputs or []) > 1)
        allowed_routes = list(node.outputs or [])

        instr = node_runtime.instructions
        if multi_output and allowed_routes:
            router_instr = build_router_instruction(agent_name, node.id, allowed_routes, friendly_map)
            instr = router_instr + "\n\n" + instr if instr else router_instr

        # Base kwargs
        kwargs: Dict[str, Any] = {
            "name": agent_name,
            "instructions": instr,
            "model": self.window.core.agents.provider.get_openai_model(node_runtime.model),
        }

        # Tools
        tool_kwargs = append_tools(
            tools=function_tools or [],
            window=self.window,
            model=node_runtime.model,
            preset=preset,
            allow_local_tools=node_runtime.allow_local_tools,
            allow_remote_tools=node_runtime.allow_remote_tools,
        )
        kwargs.update(tool_kwargs)

        # Experts/handoffs if any
        if handoffs_enabled:
            experts = get_experts(
                window=self.window,
                preset=preset,
                verbose=False,
                tools=function_tools or [],
            )
            if experts:
                kwargs["handoffs"] = experts

        # Build instance
        instance = OpenAIAgent(**kwargs)
        self.logger.debug(
            f"Built agent {node.id} ({agent_name}), "
            f"multi_output={multi_output}, routes={allowed_routes}, model={node_runtime.model.name}"
        )

        return BuiltAgent(
            instance=instance,
            name=agent_name,
            instructions=instr,
            multi_output=multi_output,
            allowed_routes=allowed_routes,
        )