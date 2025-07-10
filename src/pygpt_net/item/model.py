#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.01 01:00:00                  #
# ================================================== #

import json

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_VISION,
    MULTIMODAL_IMAGE,
    MODE_AUDIO,
    MULTIMODAL_AUDIO,
)

class ModelItem:

    OPENAI_COMPATIBLE = [
        "anthropic",
        "openai",
        "azure_openai",
        "google",
        "local_ai",
        "mistral_ai",
        "perplexity",
        "deepseek_api",
        "x_ai",
    ]

    def __init__(self, id=None):
        """
        Model data item

        :param id: Model ID
        """
        self.id = id
        self.name = None
        self.mode = ["chat"]
        self.langchain = {}
        self.llama_index = {}
        self.multimodal = ["text"]  # multimodal support: image, audio, etc.
        self.input = ["text"]  # multimodal support: image, audio, etc.
        self.output = ["text"]  # multimodal support: image, audio, etc.
        self.ctx = 0
        self.tokens = 0
        self.default = False
        self.imported = False
        self.provider = "openai"  # default provider
        self.extra = {}

    def from_dict(self, data: dict):
        """
        Load data from dict

        :param data: dict
        """
        if 'id' in data:
            self.id = data['id']
        if 'name' in data:
            self.name = data['name']
        if 'mode' in data:
            mode = data['mode'].replace(' ', '')
            self.mode = mode.split(',')
        if 'input' in data:
            input = data['input'].replace(' ', '')
            self.input = input.split(',')
        if 'output' in data:
            output = data['output'].replace(' ', '')
            self.output = output.split(',')
        if 'ctx' in data:
            self.ctx = data['ctx']
        if 'tokens' in data:
            self.tokens = data['tokens']
        if 'default' in data:
            self.default = data['default']
        if 'extra' in data:
            self.extra = data['extra']
        if 'imported' in data:
            self.imported = data['imported']
        if 'provider' in data:
            self.provider = data['provider']

        # langchain
        """
        if 'langchain.provider' in data:
            self.langchain['provider'] = data['langchain.provider']
        if 'langchain.mode' in data:
            if data['langchain.mode'] is None or data['langchain.mode'] == "":
                self.langchain['mode'] = []
            else:
                mode = data['langchain.mode'].replace(' ', '')
                self.langchain['mode'] = mode.split(',')
        if 'langchain.args' in data:
            self.langchain['args'] = data['langchain.args']
        if 'langchain.env' in data:
            self.langchain['env'] = data['langchain.env']
        """
        
        # llama index
        if 'llama_index.provider' in data:
            self.llama_index['provider'] = data['llama_index.provider']  # backward compatibility < v2.5.20
        """
        if 'llama_index.mode' in data:
            if data['llama_index.mode'] is None or data['llama_index.mode'] == "":
                self.llama_index['mode'] = []
            else:
                mode = data['llama_index.mode'].replace(' ', '')
                self.llama_index['mode'] = mode.split(',')
        """
        if 'llama_index.args' in data:
            self.llama_index['args'] = data['llama_index.args']
        if 'llama_index.env' in data:
            self.llama_index['env'] = data['llama_index.env']

    def to_dict(self) -> dict:
        """
        Return data as dict

        :return: dict
        """
        data = {}
        data['id'] = self.id
        data['name'] = self.name
        data['mode'] = ','.join(self.mode)
        data['input'] = ','.join(self.input)
        data['output'] = ','.join(self.output)
        # data['langchain'] = self.langchain
        data['ctx'] = self.ctx
        data['tokens'] = self.tokens
        data['default'] = self.default
        data['extra'] = self.extra
        data['imported'] = self.imported
        data['provider'] = self.provider

        # data['langchain.provider'] = None
        # data['langchain.mode'] = ""
        # data['langchain.args'] = []
        # data['langchain.env'] = []
        # data['llama_index.provider'] = None
        # data['llama_index.mode'] = ""
        data['llama_index.args'] = []
        data['llama_index.env'] = []


        # langchain
        """
        if 'provider' in self.langchain:
            data['langchain.provider'] = self.langchain['provider']        
        if 'mode' in self.langchain:
            data['langchain.mode'] = ",".join(self.langchain['mode'])
        if 'args' in self.langchain:
            # old versions support
            if isinstance(self.langchain['args'], dict):
                for key, value in self.langchain['args'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    item['type'] = 'str'
                    data['langchain.args'].append(item)
            elif isinstance(self.langchain['args'], list):
                data['langchain.args'] = self.langchain['args']
        if 'env' in self.langchain:
            # old versions support
            if isinstance(self.langchain['env'], dict):
                for key, value in self.langchain['env'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    data['langchain.env'].append(item)
            elif isinstance(self.langchain['env'], list):
                data['langchain.env'] = self.langchain['env']
        """

        # llama_index
        # if 'provider' in self.llama_index:
            # data['llama_index.provider'] = self.llama_index['provider']
        # if 'mode' in self.llama_index:
            # data['llama_index.mode'] = ",".join(self.llama_index['mode'])
        if 'args' in self.llama_index:
            # old versions support
            if isinstance(self.llama_index['args'], dict):
                for key, value in self.llama_index['args'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    item['type'] = 'str'
                    data['llama_index.args'].append(item)
            elif isinstance(self.llama_index['args'], list):
                data['llama_index.args'] = self.llama_index['args']
        if 'env' in self.llama_index:
            # old versions support
            if isinstance(self.llama_index['env'], dict):
                for key, value in self.llama_index['env'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    data['llama_index.env'].append(item)
            elif isinstance(self.llama_index['env'], list):
                data['llama_index.env'] = self.llama_index['env']

        return data

    def is_supported(self, mode: str) -> bool:
        """
        Check if model supports mode

        :param mode: Mode
        :return: True if supported
        """
        if mode == MODE_CHAT and not self.is_openai_supported():
            # only OpenAI API compatible models are supported in Chat mode
            return False
        return mode in self.mode

    def is_multimodal(self) -> bool:
        """
        Check if model is multimodal

        :return: True if multimodal
        """
        return len(self.multimodal) > 0

    def is_openai_supported(self) -> bool:
        """
        Check if model is supported by OpenAI API (or compatible)

        :return: True if OpenAI compatible
        """
        return self.provider in self.OPENAI_COMPATIBLE

    def is_gpt(self) -> bool:
        """
        Check if model is supported by OpenAI Responses API

        :return: True if OpenAI Responses API compatible
        """
        if (self.id.startswith("gpt-")
                or self.id.startswith("chatgpt")
                or self.id.startswith("o1")
                or self.id.startswith("o3")
                or self.id.startswith("o4")
                or self.id.startswith("o5")
                or self.id.startswith("codex-")):
            return True
        return False

    def is_ollama(self) -> bool:
        """
        Check if model is Ollama

        :return: True if Ollama
        """
        if self.provider == "ollama":
            return True
        if self.llama_index is None:
            return False
        if self.llama_index.get("provider") is None:
            return False
        return "ollama" in self.llama_index.get("provider", "")

    def get_provider(self):
        return self.provider

    def get_ollama_model(self) -> str:
        """
        Get Ollama model ID

        :return: model ID
        """
        if "args" in self.llama_index:
            for arg in self.llama_index["args"]:
                if arg["name"] == "model":
                    return arg["value"]
        return ""

    def has_mode(self, mode: str) -> bool:
        """
        Check if model has mode

        :param mode: Mode
        :return: True if supported
        """
        return mode in self.mode

    def add_mode(self, mode: str):
        """
        Add mode

        :param mode: Mode
        """
        if mode not in self.mode:
            self.mode.append(mode)

    def remove_mode(self, mode: str):
        """
        Remove mode

        :param mode: Mode
        """
        if mode in self.mode:
            self.mode.remove(mode)

    def is_image_input(self) -> bool:
        """
        Check if model supports image input

        :return: True if supports image input
        """
        if MODE_VISION in self.mode or MULTIMODAL_IMAGE in self.input:
            return True
        return False

    def is_audio_input(self) -> bool:
        """
        Check if model supports audio input

        :return: True if supports audio input
        """
        if MODE_AUDIO in self.mode or MULTIMODAL_AUDIO in self.input:
            return True
        return False

    def dump(self) -> str:
        """
        Dump event to json string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self) -> str:
        """
        To string

        :return: Dumped JSON string
        """
        return self.dump()
