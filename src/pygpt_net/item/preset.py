#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.30 00:00:00                  #
# ================================================== #

import json
import uuid


class PresetItem:
    def __init__(self):
        self.uuid = None
        self.name = "*"
        self.ai_name = ""
        self.user_name = ""
        self.prompt = ""
        self.chat = False
        self.completion = False
        self.img = False
        self.vision = False
        self.langchain = False
        self.assistant = False
        self.llama_index = False
        self.agent = False
        self.agent_llama = False
        self.agent_openai = False
        self.expert = False
        self.audio = False
        self.research = False
        self.computer = False
        self.temperature = 1.0
        self.filename = None
        self.model = None
        self.version = None
        self.experts = []  # agent mode
        self.idx = None
        self.agent_provider = None
        self.agent_provider_openai = None
        self.assistant_id = ""
        self.description = ""
        self.enabled = True
        self.tools = {
            "function": [],
        }
        self.remote_tools = []

    def get_id(self) -> str:
        return self.filename

    def to_dict(self):
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "ai_name": self.ai_name,
            "user_name": self.user_name,
            "prompt": self.prompt,
            "chat": self.chat,
            "completion": self.completion,
            "img": self.img,
            "vision": self.vision,
            "langchain": self.langchain,
            "assistant": self.assistant,
            "llama_index": self.llama_index,
            "agent": self.agent,
            "agent_llama": self.agent_llama,
            "agent_openai": self.agent_openai,
            "expert": self.expert,
            "audio": self.audio,
            "research": self.research,
            "computer": self.computer,
            "temperature": self.temperature,
            "filename": self.filename,
            "model": self.model,
            "tool.function": self.tools["function"],
            "experts": self.experts,
            "idx": self.idx,
            "agent_provider": self.agent_provider,
            "agent_provider_openai": self.agent_provider_openai,
            "assistant_id": self.assistant_id,
            "enabled": self.enabled,
            "description": self.description,
            "remote_tools": self.remote_tools,
        }

    def from_dict(self, data):
        if "uuid" in data:
            self.uuid = uuid.UUID(data["uuid"])
        if "name" in data:
            self.name = data["name"]
        if "ai_name" in data:
            self.ai_name = data["ai_name"]
        if "user_name" in data:
            self.user_name = data["user_name"]
        if "prompt" in data:
            self.prompt = data["prompt"]
        if "chat" in data:
            self.chat = data["chat"]
        if "completion" in data:
            self.completion = data["completion"]
        if "img" in data:
            self.img = data["img"]
        if "vision" in data:
            self.vision = data["vision"]
        if "langchain" in data:
            self.langchain = data["langchain"]
        if "assistant" in data:
            self.assistant = data["assistant"]
        if "llama_index" in data:
            self.llama_index = data["llama_index"]
        if "agent" in data:
            self.agent = data["agent"]
        if "agent_llama" in data:
            self.agent_llama = data["agent_llama"]
        if "agent_openai" in data:
            self.agent_openai = data["agent_openai"]
        if "expert" in data:
            self.expert = data["expert"]
        if "audio" in data:
            self.audio = data["audio"]
        if "research" in data:
            self.research = data["research"]
        if "computer" in data:
            self.computer = data["computer"]
        if "temperature" in data:
            self.temperature = data["temperature"]
        if "filename" in data:
            self.filename = data["filename"]
        if "model" in data:
            self.model = data["model"]
        if "tool.function" in data:
            self.tools["function"] = data["tool.function"]
        if "experts" in data:
            self.experts = data["experts"]
        if "idx" in data:
            self.idx = data["idx"]
        if "agent_provider" in data:
            self.agent_provider = data["agent_provider"]
        if "agent_provider_openai" in data:
            self.agent_provider_openai = data["agent_provider_openai"]
        if "assistant_id" in data:
            self.assistant_id = data["assistant_id"]
        if "enabled" in data:
            self.enabled = data["enabled"]
        if "description" in data:
            self.description = data["description"]
        if "remote_tools" in data:
            self.remote_tools = data["remote_tools"]
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

    def __str__(self):
        """To string"""
        return self.dump()
