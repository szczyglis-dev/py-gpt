#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.01 23:00:00                  #
# ================================================== #

import json
from typing import Optional

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_VISION,
    MULTIMODAL_IMAGE,
    MODE_AUDIO,
    MULTIMODAL_AUDIO,
    OPENAI_COMPATIBLE_PROVIDERS,
    MULTIMODAL_VIDEO,
)

class ModelItem:

    def __init__(self, id: Optional[str] = None):
        """
        Model data item

        :param id: Model ID
        """
        self.ctx = 0
        self.default = False
        self.extra = {}
        self.id = id
        self.imported = False
        self.input = ["text"]  # multimodal support: image, audio, etc.
        self.langchain = {}
        self.llama_index = {}
        self.mode = ["chat"]
        self.multimodal = ["text"]  # multimodal support: image, audio, etc.
        self.name = None
        self.output = ["text"]  # multimodal support: image, audio, etc.
        self.provider = "openai"  # default provider
        self.tokens = 0
        self.tool_calls = False  # native tool calls available

    def from_dict(self, data: dict):
        """
        Load data from dict

        :param data: dict
        """
        if 'ctx' in data:
            self.ctx = data['ctx']
        if 'default' in data:
            self.default = data['default']
        if 'extra' in data:
            self.extra = data['extra']
        if 'id' in data:
            self.id = data['id']
        if 'imported' in data:
            self.imported = data['imported']
        if 'input' in data:
            input = data['input'].replace(' ', '')
            self.input = input.split(',')
        if 'mode' in data:
            mode = data['mode'].replace(' ', '')
            self.mode = mode.split(',')
        if 'name' in data:
            self.name = data['name']
        if 'output' in data:
            output = data['output'].replace(' ', '')
            self.output = output.split(',')
        if 'provider' in data:
            self.provider = data['provider']
        if 'tokens' in data:
            self.tokens = data['tokens']
        if 'tool_calls' in data:
            self.tool_calls = data['tool_calls']
        
        # llama index
        if 'llama_index.provider' in data:
            self.llama_index['provider'] = data['llama_index.provider']  # backward compatibility < v2.5.20
        if 'llama_index.args' in data:
            self.llama_index['args'] = data['llama_index.args']
        if 'llama_index.env' in data:
            self.llama_index['env'] = data['llama_index.env']

    def to_dict(self) -> dict:
        """
        Return data as dict

        :return: dict
        """
        data = {
            'id': self.id,
            'name': self.name,
            'mode': ','.join(self.mode),
            'input': ','.join(self.input),
            'output': ','.join(self.output),
            'ctx': self.ctx,
            'tokens': self.tokens,
            'default': self.default,
            'extra': self.extra,
            'imported': self.imported,
            'provider': self.provider,
            'tool_calls': self.tool_calls,
            'llama_index.args': [],
            'llama_index.env': []
        }

        if 'args' in self.llama_index:
            # old versions support
            if isinstance(self.llama_index['args'], dict):
                for key, value in self.llama_index['args'].items():
                    item = {
                        'name': key,
                        'value': value,
                        'type': 'str'
                    }
                    data['llama_index.args'].append(item)
            elif isinstance(self.llama_index['args'], list):
                data['llama_index.args'] = self.llama_index['args']

        if 'env' in self.llama_index:
            # old versions support
            if isinstance(self.llama_index['env'], dict):
                for key, value in self.llama_index['env'].items():
                    item = {
                        'name': key,
                        'value': value
                    }
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
        return self.provider in OPENAI_COMPATIBLE_PROVIDERS

    def is_gpt(self) -> bool:
        """
        Check if model is supported by OpenAI Responses API

        :return: True if OpenAI Responses API compatible
        """
        if self.id.startswith("gpt-oss"):
            return False

        if (self.id.startswith("gpt-")
                or self.id.startswith("chatgpt")
                or self.id.startswith("o1")
                or self.id.startswith("o3")
                or self.id.startswith("o4")
                or self.id.startswith("o5")
                or self.id.startswith("codex-")
                or self.id.startswith("dall-e-")
                or self.id.startswith("computer-use")):
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

    def get_provider(self) -> str:
        """
        Get model provider

        :return: Provider name
        """
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
        if MULTIMODAL_IMAGE in self.input:
            return True
        return False

    def is_image_output(self) -> bool:
        """
        Check if model supports image output

        :return: True if supports image output
        """
        if "image" in self.output or MODE_VISION in self.mode:
            return True
        return False

    def is_audio_input(self) -> bool:
        """
        Check if model supports audio input

        :return: True if supports audio input
        """
        if MULTIMODAL_AUDIO in self.input:
            return True
        return False

    def is_audio_output(self) -> bool:
        """
        Check if model supports audio output

        :return: True if supports audio output
        """
        if MULTIMODAL_AUDIO in self.output:
            return True
        return False

    def is_video_input(self) -> bool:
        """
        Check if model supports video input

        :return: True if supports video input
        """
        if MULTIMODAL_VIDEO in self.input:
            return True
        return False

    def is_video_output(self) -> bool:
        """
        Check if model supports video output

        :return: True if supports video output
        """
        if MULTIMODAL_VIDEO in self.output:
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
