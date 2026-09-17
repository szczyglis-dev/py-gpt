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

import copy
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..mode import AgentMode
from ..prompts import (
    CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY,
    CUSTOM_PRIMARY_PROMPT_CONFIG_KEY,
    CUSTOM_SWARM_PROMPT_CONFIG_KEY,
    ORCHESTRATOR_BASE_PROMPT,
    PRIMARY_AGENT_BASE_PROMPT,
    SWARM_BASE_PROMPT,
)


CUSTOM_AGENTS_CONFIG_KEY = "agent.v2.custom_agents"


class AgentEditor:
    """Registry/storage facade for built-in and user-defined Chat with Agents roles.

    Built-in prompt overrides intentionally keep using the pre-2.8.22 config keys.
    User-created agents are stored in ``agent.v2.custom_agents`` and run on the
    Orchestrator execution/tool surface with one complete editable system prompt.
    """

    BUILTIN_IDS = ("chat", "orchestrator", "swarm")

    _BUILTINS = {
        "chat": {
            "id": "chat",
            "name": "Chat",
            "label_key": "agent.v2.mode.chat",
            "description_key": "settings.agent.v2.prompt.primary.custom.desc",
            "runtime_mode": AgentMode.PRIMARY_AGENT,
            "prompt_config_key": CUSTOM_PRIMARY_PROMPT_CONFIG_KEY,
            "default_prompt": str(PRIMARY_AGENT_BASE_PROMPT),
        },
        "orchestrator": {
            "id": "orchestrator",
            "name": "Orchestrator",
            "label_key": "agent.v2.mode.orchestrator",
            "description_key": "settings.agent.v2.prompt.orchestrator.custom.desc",
            "runtime_mode": AgentMode.ORCHESTRATOR,
            "prompt_config_key": CUSTOM_ORCHESTRATOR_PROMPT_CONFIG_KEY,
            "default_prompt": str(ORCHESTRATOR_BASE_PROMPT),
        },
        "swarm": {
            "id": "swarm",
            "name": "Swarm",
            "label_key": "agent.v2.mode.swarm",
            "description_key": "settings.agent.v2.prompt.swarm.custom.desc",
            "runtime_mode": AgentMode.SWARM,
            "prompt_config_key": CUSTOM_SWARM_PROMPT_CONFIG_KEY,
            "default_prompt": str(SWARM_BASE_PROMPT),
        },
    }

    _ALIASES = {
        "primary": "chat",
        "primary_agent": "chat",
        "primary-agent": "chat",
        "swarm_mode": "swarm",
        "swarm-mode": "swarm",
    }

    def __init__(self, window=None):
        self.window = window

    def _config(self):
        return self.window.core.config

    @classmethod
    def normalize_builtin_id(cls, value: Any) -> str:
        if isinstance(value, AgentMode):
            mapping = {
                AgentMode.PRIMARY_AGENT: "chat",
                AgentMode.ORCHESTRATOR: "orchestrator",
                AgentMode.SWARM: "swarm",
            }
            return mapping.get(value, "")
        raw = str(value or "").strip().lower()
        raw = cls._ALIASES.get(raw, raw)
        return raw if raw in cls.BUILTIN_IDS else ""

    def get_custom_agents(self) -> List[Dict[str, str]]:
        """Return normalized custom agents in persisted order."""
        raw = self._config().get(CUSTOM_AGENTS_CONFIG_KEY, [])
        if not isinstance(raw, list):
            return []
        items: List[Dict[str, str]] = []
        seen = set()
        for row in raw:
            if not isinstance(row, dict):
                continue
            agent_id = str(row.get("id") or "").strip()
            if not agent_id or agent_id in seen or self.normalize_builtin_id(agent_id):
                continue
            seen.add(agent_id)
            items.append({
                "id": agent_id,
                "name": str(row.get("name") or "").strip(),
                "system_prompt": str(row.get("system_prompt") or ""),
            })
        return items

    def _store_custom_agents(self, items: List[Dict[str, str]]) -> None:
        self._config().set(CUSTOM_AGENTS_CONFIG_KEY, copy.deepcopy(items))

    def get_agents(self) -> List[Dict[str, Any]]:
        """Return built-ins first, followed by user-defined agents."""
        items: List[Dict[str, Any]] = []
        for agent_id in self.BUILTIN_IDS:
            row = dict(self._BUILTINS[agent_id])
            row["built_in"] = True
            items.append(row)
        for custom in self.get_custom_agents():
            row = dict(custom)
            row.update({
                "built_in": False,
                "label_key": "",
                "description_key": "",
                "runtime_mode": AgentMode.ORCHESTRATOR,
            })
            items.append(row)
        return items

    def get(self, agent_id: Any) -> Optional[Dict[str, Any]]:
        builtin_id = self.normalize_builtin_id(agent_id)
        if builtin_id:
            row = dict(self._BUILTINS[builtin_id])
            row["built_in"] = True
            return row
        wanted = str(agent_id or "").strip()
        for row in self.get_custom_agents():
            if row["id"] == wanted:
                item = dict(row)
                item.update({
                    "built_in": False,
                    "label_key": "",
                    "description_key": "",
                    "runtime_mode": AgentMode.ORCHESTRATOR,
                })
                return item
        return None

    def resolve_selection(self, value: Any) -> Tuple[str, AgentMode, Optional[Dict[str, Any]]]:
        """Resolve persisted selector value into id, execution mode and custom row."""
        builtin_id = self.normalize_builtin_id(value)
        if builtin_id:
            row = self.get(builtin_id)
            return builtin_id, row["runtime_mode"], None
        wanted = str(value or "").strip()
        row = self.get(wanted)
        if row is not None and not row.get("built_in"):
            return wanted, AgentMode.ORCHESTRATOR, row
        return "chat", AgentMode.PRIMARY_AGENT, None

    def editable_values(self, agent_id: Any) -> Optional[Dict[str, Any]]:
        row = self.get(agent_id)
        if row is None:
            return None
        if row.get("built_in"):
            prompt_key = row["prompt_config_key"]
            return {
                **row,
                "name": row["name"],
                "system_prompt": str(self._config().get(prompt_key, "") or ""),
            }
        return row

    def create(self, name: str = "New agent") -> str:
        agent_id = str(uuid.uuid4())
        items = self.get_custom_agents()
        items.append({
            "id": agent_id,
            "name": str(name or "New agent").strip() or "New agent",
            "system_prompt": "",
        })
        self._store_custom_agents(items)
        return agent_id

    def save(
            self,
            agent_id: Any,
            name: str,
            system_prompt: str,
    ) -> bool:
        builtin_id = self.normalize_builtin_id(agent_id)
        if builtin_id:
            row = self._BUILTINS[builtin_id]
            self._config().set(row["prompt_config_key"], str(system_prompt or ""))
            return True

        wanted = str(agent_id or "").strip()
        items = self.get_custom_agents()
        for row in items:
            if row["id"] == wanted:
                row["name"] = str(name or "").strip()
                row["system_prompt"] = str(system_prompt or "")
                self._store_custom_agents(items)
                return True
        return False

    def delete(self, agent_id: Any) -> bool:
        if self.normalize_builtin_id(agent_id):
            return False
        wanted = str(agent_id or "").strip()
        items = self.get_custom_agents()
        filtered = [row for row in items if row["id"] != wanted]
        if len(filtered) == len(items):
            return False
        self._store_custom_agents(filtered)
        return True

    def get_default_main_prompt(self, agent_id: Any) -> str:
        """Return the complete built-in prompt, including integrated execution rules."""
        builtin_id = self.normalize_builtin_id(agent_id)
        if builtin_id:
            return str(self._BUILTINS[builtin_id]["default_prompt"])
        # Custom workflows start from the complete Orchestrator template on request
        # only; there is deliberately no implicit runtime fallback/injection.
        return str(ORCHESTRATOR_BASE_PROMPT)
