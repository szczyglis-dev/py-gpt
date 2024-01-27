#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 15:00:00                  #
# ================================================== #

import json


class PresetItem:
    def __init__(self):
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
        self.temperature = 1.0
        self.filename = None
        self.model = None
        self.version = None

    def to_dict(self):
        return {
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
            "temperature": self.temperature,
            "filename": self.filename,
            "model": self.model,
        }

    def from_dict(self, data):
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
        if "temperature" in data:
            self.temperature = data["temperature"]
        if "filename" in data:
            self.filename = data["filename"]
        if "model" in data:
            self.model = data["model"]
        return self

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
