#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.12 12:15:00                  #
# ================================================== #

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass(slots=True)
class PresetItem:
    agent: bool = False
    agent_llama: bool = False
    agent_openai: bool = False
    agent_v2: bool = False
    agent_v2_allow_local_tools: bool = True
    agent_v2_allow_remote_tools: bool = True
    agent_skills: List[str] = field(default_factory=list)
    agent_skills_use: bool = False
    agent_provider: Optional[str] = None
    agent_provider_openai: Optional[str] = None
    ai_avatar: str = ""
    ai_name: str = ""
    ai_personalize: bool = False
    assistant: bool = False
    assistant_id: str = ""
    audio: bool = False
    chat: bool = False
    completion: bool = False
    computer: bool = False
    description: str = ""
    enabled: bool = True
    expert: bool = False
    experts: List[Any] = field(default_factory=list)  # agent mode
    extra: Dict[str, Any] = field(default_factory=dict)
    filename: Optional[str] = None
    img: bool = False
    idx: Optional[int] = None
    langchain: bool = False
    llama_index: bool = False
    model: Optional[str] = None
    model_use: bool = True
    mcp: List[str] = field(default_factory=list)
    mcp_use: bool = False
    name: str = "*"
    plugin_preset: Optional[str] = None
    plugin_preset_use: bool = False
    prompt: str = ""
    research: bool = False
    idx_use: bool = True
    remote_tools: List[Any] = field(default_factory=list)
    tools: Dict[str, Any] = field(default_factory=lambda: {"function": []})
    uuid: Optional[str] = None
    user_name: str = ""
    version: Optional[str] = None
    vision: bool = False

    def __init__(self):
        self.agent = False
        self.agent_llama = False
        self.agent_openai = False
        self.agent_v2 = False
        self.agent_v2_allow_local_tools = True
        self.agent_v2_allow_remote_tools = True
        self.agent_skills = []
        self.agent_skills_use = False
        self.agent_provider = None
        self.agent_provider_openai = None
        self.ai_avatar = ""
        self.ai_name = ""
        self.ai_personalize = False
        self.assistant = False
        self.assistant_id = ""
        self.audio = False
        self.chat = False
        self.completion = False
        self.computer = False
        self.description = ""
        self.enabled = True
        self.expert = False
        self.experts = []  # agent mode
        self.extra = {}
        self.filename = None
        self.img = False
        self.idx = None
        self.langchain = False
        self.llama_index = False
        self.model = None
        self.model_use = True
        self.mcp = []
        self.mcp_use = False
        self.name = "*"
        self.plugin_preset = None
        self.plugin_preset_use = False
        self.prompt = ""
        self.research = False
        self.idx_use = True
        self.remote_tools = []
        self.tools = {
            "function": [],
        }
        self.uuid = None
        self.user_name = ""
        self.version = None
        self.vision = False

    def get_id(self) -> str:
        """
        Get preset ID

        :return: ID of the preset
        """
        return self.filename

    def to_dict(self) -> dict:
        """
        Convert preset item to dict

        :return: dict representation of the preset item
        """
        return {
            "agent": self.agent,
            "agent_llama": self.agent_llama,
            "agent_openai": self.agent_openai,
            "agent_v2": self.agent_v2,
            "agent_v2_allow_local_tools": self.agent_v2_allow_local_tools,
            "agent_v2_allow_remote_tools": self.agent_v2_allow_remote_tools,
            "agent_skills": self.agent_skills,
            "agent_skills_use": self.agent_skills_use,
            "agent_provider": self.agent_provider,
            "agent_provider_openai": self.agent_provider_openai,
            "ai_avatar": self.ai_avatar,
            "ai_name": self.ai_name,
            "ai_personalize": self.ai_personalize,
            "assistant": self.assistant,
            "assistant_id": self.assistant_id,
            "audio": self.audio,
            "chat": self.chat,
            "completion": self.completion,
            "computer": self.computer,
            "description": self.description,
            "enabled": self.enabled,
            "expert": self.expert,
            "experts": self.experts,
            "extra": self.extra,
            "filename": self.filename,
            "img": self.img,
            "idx": self.idx,
            "langchain": self.langchain,
            "llama_index": self.llama_index,
            "model": self.model,
            "model_use": self.model_use,
            "mcp": self.mcp,
            "mcp_use": self.mcp_use,
            "name": self.name,
            "plugin_preset": self.plugin_preset,
            "plugin_preset_use": self.plugin_preset_use,
            "prompt": self.prompt,
            "remote_tools": self.remote_tools,
            "research": self.research,
            "idx_use": self.idx_use,
            "tool.function": self.tools["function"],
            "user_name": self.user_name,
            "uuid": str(self.uuid),
            "version": self.version,
            "vision": self.vision,
        }

    def from_dict(self, data: dict):
        """
        Load data from dict

        :param data: data dict
        """
        if "agent" in data:
            self.agent = data["agent"]
        if "agent_llama" in data:
            self.agent_llama = data["agent_llama"]
        if "agent_openai" in data:
            self.agent_openai = data["agent_openai"]
        if "agent_v2" in data:
            self.agent_v2 = bool(data["agent_v2"])
        # Agent/Expert tool policy defaults to enabled for older presets that
        # predate these fields. Assign unconditionally so reusing a PresetItem
        # cannot leak a previous False value when the keys are absent.
        self.agent_v2_allow_local_tools = bool(data.get("agent_v2_allow_local_tools", True))
        self.agent_v2_allow_remote_tools = bool(data.get("agent_v2_allow_remote_tools", True))
        self.agent_skills_use = bool(data.get("agent_skills_use", False))
        self.agent_skills = []
        if "agent_skills" in data:
            value = data["agent_skills"]
            if isinstance(value, list):
                self.agent_skills = [str(item) for item in value if str(item).strip()]
            elif isinstance(value, str):
                self.agent_skills = [item.strip() for item in value.split(",") if item.strip()]
        if "agent_provider" in data:
            self.agent_provider = data["agent_provider"]
        if "agent_provider_openai" in data:
            self.agent_provider_openai = data["agent_provider_openai"]
        if "ai_avatar" in data:
            self.ai_avatar = data["ai_avatar"]
        if "ai_name" in data:
            self.ai_name = data["ai_name"]
        if "ai_personalize" in data:
            self.ai_personalize = data["ai_personalize"]
        if "assistant" in data:
            self.assistant = data["assistant"]
        if "assistant_id" in data:
            self.assistant_id = data["assistant_id"]
        if "audio" in data:
            self.audio = data["audio"]
        if "chat" in data:
            self.chat = data["chat"]
        if "completion" in data:
            self.completion = data["completion"]
        if "computer" in data:
            self.computer = data["computer"]
        if "description" in data:
            self.description = data["description"]
        if "enabled" in data:
            self.enabled = data["enabled"]
        if "expert" in data:
            self.expert = data["expert"]
        if "experts" in data:
            self.experts = data["experts"]
        if "extra" in data:
            self.extra = data["extra"]
        if "filename" in data:
            self.filename = data["filename"]
        if "img" in data:
            self.img = data["img"]
        if "idx" in data:
            self.idx = data["idx"]
        if "langchain" in data:
            self.langchain = data["langchain"]
        if "llama_index" in data:
            self.llama_index = data["llama_index"]
        if "model" in data:
            self.model = data["model"]
        # Model/RAG restore was historically unconditional, therefore older
        # presets must keep that behavior unless the new switches are changed.
        self.model_use = bool(data.get("model_use", True))
        self.mcp_use = bool(data.get("mcp_use", False))
        self.mcp = []
        if "mcp" in data:
            value = data["mcp"]
            if isinstance(value, list):
                self.mcp = [str(item) for item in value if str(item).strip()]
            elif isinstance(value, str):
                self.mcp = [item.strip() for item in value.split(",") if item.strip()]
        if "name" in data:
            self.name = data["name"]
        if "plugin_preset" in data:
            value = data["plugin_preset"]
            self.plugin_preset = str(value).strip() if value not in (None, "", "_") else None
        else:
            self.plugin_preset = None
        self.plugin_preset_use = bool(data.get("plugin_preset_use", False))
        if "prompt" in data:
            self.prompt = data["prompt"]
        if "remote_tools" in data:
            self.remote_tools = data["remote_tools"]
        if "research" in data:
            self.research = data["research"]
        self.idx_use = bool(data.get("idx_use", True))
        if "tool.function" in data:
            self.tools["function"] = data["tool.function"]
        if "user_name" in data:
            self.user_name = data["user_name"]
        if "uuid" in data:
            self.uuid = str(uuid.UUID(data["uuid"]))
        if "vision" in data:
            self.vision = data["vision"]
        return self

    def reset_modes(self):
        """
        Reset  modes
        """
        self.agent = False
        self.agent_llama = False
        self.agent_openai = False
        self.agent_v2 = False
        self.audio = False
        self.assistant = False
        self.chat = False
        self.completion = False
        self.computer = False
        self.expert = False
        self.langchain = False
        self.llama_index = False
        self.research = False
        self.vision = False

    def add_function(self, name: str, parameters: str, desc: str):
        """
        Add function to preset

        :param name: function name
        :param parameters: function parameters (JSON encoded)
        :param desc: function description
        """
        function = {
            'name': name,
            'params': parameters,
            'desc': desc,
        }
        self.tools['function'].append(function)

    def has_functions(self) -> bool:
        """
        Check if preset has functions

        :return: bool
        """
        return len(self.tools['function']) > 0

    def get_functions(self) -> list:
        """
        Return preset functions

        :return: functions
        """
        return self.tools['function']

    def dump(self):
        """
        Dump item to string

        :return: serialized item
        :rtype: str
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self) -> str:
        """
        To string

        :return: serialized item
        """
        return self.dump()