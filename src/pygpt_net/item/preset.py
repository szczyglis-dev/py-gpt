#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #


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
            "temperature": self.temperature,
            "filename": self.filename,
            "model": self.model,
        }

    def from_dict(self, data):
        self.name = data["name"]
        self.ai_name = data["ai_name"]
        self.user_name = data["user_name"]
        self.prompt = data["prompt"]
        self.chat = data["chat"]
        self.completion = data["completion"]
        self.img = data["img"]
        self.vision = data["vision"]
        self.langchain = data["langchain"]
        self.assistant = data["assistant"]
        self.temperature = data["temperature"]
        self.filename = data["filename"]
        self.model = data["model"]
        return self
