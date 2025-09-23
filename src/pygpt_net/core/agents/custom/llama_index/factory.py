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
from typing import Any, Dict, List

from llama_index.core.agent.workflow import ReActAgent, FunctionAgent

from ..schema import AgentNode
from ..router import build_router_instruction
from .utils import NodeRuntime, coerce_li_tools


@dataclass
class BuiltAgentLI:
    instance: Any
    name: str
    instructions: str
    multi_output: bool
    allowed_routes: List[str]


class AgentFactoryLI:
    """
    Build LlamaIndex ReActAgent/FunctionAgent from AgentNode + NodeRuntime and explicit LLM/tools.
    Best practice: chat_history/max_iterations przekazujemy do konstruktora agenta.
    """
    def __init__(self, window, logger) -> None:
        self.window = window
        self.logger = logger

    def build(
        self,
        *,
        node: AgentNode,
        node_runtime: NodeRuntime,
        llm: Any,                 # LLM instance (z appki lub resolve_llm)
        tools: List[Any],         # BaseTool list
        friendly_map: Dict[str, str],
        force_router: bool = False,
        chat_history: List[Any] = None,
        max_iterations: int = 10,
    ) -> BuiltAgentLI:
        agent_name = (node.name or "").strip() or f"Agent {node.id}"

        multi_output = force_router or (len(node.outputs or []) > 1)
        allowed_routes = list(node.outputs or [])

        instr = node_runtime.instructions
        if multi_output and allowed_routes:
            router_instr = build_router_instruction(agent_name, node.id, allowed_routes, friendly_map)
            instr = router_instr + "\n\n" + instr if instr else router_instr

        node_tools = tools if (node_runtime.allow_local_tools or node_runtime.allow_remote_tools) else []

        if multi_output:
            agent_cls = FunctionAgent  # routers behave better with FunctionAgent (JSON compliance)
        else:
            agent_cls = FunctionAgent if node_tools else ReActAgent
        kwargs: Dict[str, Any] = {
            "name": agent_name,
            "system_prompt": instr,
            "llm": llm,
            "chat_history": chat_history or [],
            "max_iterations": int(max_iterations),
        }
        if node_tools:
            kwargs["tools"] = coerce_li_tools(node_tools)

        instance = agent_cls(**kwargs)
        self.logger.debug(
            f"[li] Built agent {node.id} ({agent_name}), multi_output={multi_output}, routes={allowed_routes}"
        )
        return BuiltAgentLI(
            instance=instance,
            name=agent_name,
            instructions=instr,
            multi_output=multi_output,
            allowed_routes=allowed_routes,
        )