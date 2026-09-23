#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.23 15:30:00                  #
# ================================================== #

from .agents import AgentsV2

__all__ = [
    "AgentsV2",
    "AgentsV2Runtime",
    "RuntimeInput",
    "RuntimeOutput",
    "AgentRuntimeStrategy",
    "AgentToolSurface",
    "get_agent_strategy",
    "AgentDelegateBridge",
    "AgentEditor",
    "CUSTOM_AGENTS_CONFIG_KEY",
    "AgentMode",
    "AGENT_MODE",
    "AGENT_MODE_CONFIG_KEY",
    "AGENT_MODE_CONFIG_DEFAULT",
]


def __getattr__(name):
    """Load non-facade Agents v2 symbols on demand.

    Startup only needs :class:`AgentsV2`. Runtime/contracts/strategy modules pull
    LlamaIndex and structured-output dependencies, so they are intentionally
    deferred until code explicitly asks for those public package exports.
    """
    if name == "AgentsV2Runtime":
        from .runtime import AgentsV2Runtime
        return AgentsV2Runtime
    if name in {"RuntimeInput", "RuntimeOutput"}:
        from .contracts import RuntimeInput, RuntimeOutput
        return {"RuntimeInput": RuntimeInput, "RuntimeOutput": RuntimeOutput}[name]
    if name in {"AgentRuntimeStrategy", "AgentToolSurface", "get_agent_strategy"}:
        from .strategy import AgentRuntimeStrategy, AgentToolSurface, get_agent_strategy
        return {
            "AgentRuntimeStrategy": AgentRuntimeStrategy,
            "AgentToolSurface": AgentToolSurface,
            "get_agent_strategy": get_agent_strategy,
        }[name]
    if name == "AgentDelegateBridge":
        from .delegation import AgentDelegateBridge
        return AgentDelegateBridge
    if name in {"AgentEditor", "CUSTOM_AGENTS_CONFIG_KEY"}:
        from .editor import AgentEditor, CUSTOM_AGENTS_CONFIG_KEY
        return {"AgentEditor": AgentEditor, "CUSTOM_AGENTS_CONFIG_KEY": CUSTOM_AGENTS_CONFIG_KEY}[name]
    if name in {"AgentMode", "AGENT_MODE", "AGENT_MODE_CONFIG_KEY", "AGENT_MODE_CONFIG_DEFAULT"}:
        from .mode import AGENT_MODE, AGENT_MODE_CONFIG_DEFAULT, AGENT_MODE_CONFIG_KEY, AgentMode
        return {
            "AgentMode": AgentMode,
            "AGENT_MODE": AGENT_MODE,
            "AGENT_MODE_CONFIG_KEY": AGENT_MODE_CONFIG_KEY,
            "AGENT_MODE_CONFIG_DEFAULT": AGENT_MODE_CONFIG_DEFAULT,
        }[name]
    raise AttributeError(name)
