#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
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
    name: str = "*"
    prompt: str = ""
    research: bool = False
    remote_tools: List[Any] = field(default_factory=list)
    temperature: float = 1.0
    tools: Dict[str, Any] = field(default_factory=lambda: {"function": []})
    uuid: Optional[str] = None
    user_name: str = ""
    version: Optional[str] = None
    vision: bool = False

    def __init__(self):
        self.agent = False
        self.agent_llama = False
        self.agent_openai = False
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
        self.name = "*"
        self.prompt = ""
        self.research = False
        self.remote_tools = []
        self.temperature = 1.0
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
            "name": self.name,
            "prompt": self.prompt,
            "remote_tools": self.remote_tools,
            "research": self.research,
            "temperature": self.temperature,
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
        if "name" in data:
            self.name = data["name"]
        if "prompt" in data:
            self.prompt = data["prompt"]
        if "remote_tools" in data:
            self.remote_tools = data["remote_tools"]
        if "research" in data:
            self.research = data["research"]
        if "temperature" in data:
            self.temperature = data["temperature"]
        if "tool.function" in data:
            self.tools["function"] = data["tool.function"]
        if "user_name" in data:
            self.user_name = data["user_name"]
        if "uuid" in data:
            self.uuid = uuid.UUID(data["uuid"])
        if "vision" in data:
            self.vision = data["vision"]
        return self

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