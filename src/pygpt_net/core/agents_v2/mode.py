#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 11:00:00                  #
# ================================================== #

from enum import Enum
from typing import Any


class AgentMode(str, Enum):
    """Agents v2 top-level execution strategies.

    Keep this enum as the stable extension point for future runtimes/UI selectors.
    """

    ORCHESTRATOR = "orchestrator"
    PRIMARY_AGENT = "primary_agent"
    SWARM = "swarm"

    @classmethod
    def coerce(cls, value: Any) -> "AgentMode":
        if isinstance(value, cls):
            return value
        raw = str(value or "").strip().lower()
        aliases = {
            "chat": cls.PRIMARY_AGENT,
            "orchestrator": cls.ORCHESTRATOR,
            "primary": cls.PRIMARY_AGENT,
            "primary_agent": cls.PRIMARY_AGENT,
            "primary-agent": cls.PRIMARY_AGENT,
            "swarm": cls.SWARM,
            "swarm_mode": cls.SWARM,
            "swarm-mode": cls.SWARM,
        }
        return aliases.get(raw, AGENT_MODE)


# Stable config contract used by the Agents v2 UI selector. Keep the persisted
# value for PRIMARY_AGENT as ``chat`` so the user-facing mode name can stay
# decoupled from the internal runtime strategy name.
AGENT_MODE_CONFIG_KEY = "agent.v2.mode"
AGENT_MODE_CONFIG_DEFAULT = "chat"

# Code-level fallback used when config/runtime context does not provide a mode.
AGENT_MODE = AgentMode.PRIMARY_AGENT
