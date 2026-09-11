#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 23:55:00                  #
# ================================================== #

from typing import Dict, List, Optional

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_EXPERT,
    TOOL_EXPERT_CALL_NAME,
    TOOL_EXPERT_CALL_DESCRIPTION,
    TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION,
    TOOL_EXPERT_CALL_PARAM_INSTRUCTION_DESCRIPTION,
    TOOL_EXPERT_CALL_PARAM_SYSTEM_PROMPT_DESCRIPTION,
)
from pygpt_net.item.preset import PresetItem


class Experts:
    """Expert preset registry and expert_call tool definition.

    Expert execution itself is handled by the regular Experts plugin/tool flow.
    This core class intentionally contains no reply/worker orchestration.
    """

    def __init__(self, window=None):
        self.window = window

    def agent_enabled(self) -> bool:
        """Return True when legacy Agent mode owns the available expert list."""
        return self.window.controller.agent.legacy.enabled()

    def exists(self, id: str) -> bool:
        """Check if an Expert preset exists."""
        return self.window.core.presets.has(MODE_EXPERT, id)

    def get_expert(self, id: str) -> Optional[PresetItem]:
        """Return an Expert preset by ID."""
        return self.window.core.presets.get_by_id(MODE_EXPERT, id)

    def get_experts(self) -> Dict[str, PresetItem]:
        """Return Experts currently available to the active manager/agent."""
        experts = {}
        core = self.window.core
        presets = core.presets.get_by_mode(MODE_EXPERT)

        if self.agent_enabled():
            agents = core.presets.get_by_mode(MODE_AGENT)
            agent = core.config.get("preset")
            if agent is not None and agent in agents:
                for uuid in agents[agent].experts:
                    expert = core.presets.get_by_uuid(uuid)
                    if expert is not None:
                        experts[expert.filename] = expert
        else:
            for key, expert in presets.items():
                if key.startswith("current."):
                    continue
                if not expert.enabled:
                    continue
                experts[key] = expert
        return experts

    def get_expert_name_by_id(self, id: str) -> Optional[str]:
        """Return display name for an available Expert ID."""
        expert = self.get_experts().get(id)
        return expert.name if expert is not None else None

    def count_experts(self, uuid: str) -> int:
        """Count Experts assigned to a legacy Agent preset."""
        count = 0
        core = self.window.core
        agents = core.presets.get_by_mode(MODE_AGENT)
        if uuid in agents:
            for expert_uuid in agents[uuid].experts:
                if core.presets.get_by_uuid(expert_uuid) is not None:
                    count += 1
        return count

    def get_prompt(self) -> str:
        """Build the manager prompt with the currently available Expert list."""
        prompt = self.window.core.config.get("prompt.expert") or ""
        experts_list = []
        for key, expert in self.get_experts().items():
            if key.startswith("current."):
                continue
            description = str(expert.description or "").strip()
            if description:
                experts_list.append(f" - {key}: {expert.name} ({description})")
            else:
                experts_list.append(f" - {key}: {expert.name}")
        return prompt.replace("{presets}", "\n".join(experts_list))

    def get_functions(self) -> List[Dict[str, object]]:
        """Return the standard expert_call tool definition."""
        return [
            {
                "cmd": TOOL_EXPERT_CALL_NAME,
                "instruction": TOOL_EXPERT_CALL_DESCRIPTION,
                "params": [
                    {
                        "name": "id",
                        "description": TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION,
                        "required": True,
                        "type": "str",
                    },
                    {
                        "name": "instruction",
                        "description": TOOL_EXPERT_CALL_PARAM_INSTRUCTION_DESCRIPTION,
                        "required": True,
                        "type": "str",
                    },
                    {
                        "name": "system_prompt",
                        "description": TOOL_EXPERT_CALL_PARAM_SYSTEM_PROMPT_DESCRIPTION,
                        "required": False,
                        "type": "str",
                    },
                ],
            }
        ]
