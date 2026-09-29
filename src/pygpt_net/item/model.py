#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 13:22:00
# ================================================== #

import json
from typing import Optional
from dataclasses import dataclass, field

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MULTIMODAL_IMAGE,
    MODE_AUDIO,
    MULTIMODAL_AUDIO,
    OPENAI_COMPATIBLE_PROVIDERS,
    MULTIMODAL_VIDEO,
)
from pygpt_net.provider.core.model.compat import is_openai_o_series

@dataclass(slots=True)
class ModelItem:
    id: Optional[str] = None
    ctx: int = 0
    custom_api_endpoint: str = ""
    custom_api_key: str = ""
    default: bool = False
    extra: dict = field(default_factory=dict)
    imported: bool = False
    is_hidden: bool = False
    input: list = field(default_factory=lambda: ["text"])
    langchain: dict = field(default_factory=dict)
    llama_index: dict = field(default_factory=dict)
    mode: list = field(default_factory=lambda: ["chat"])
    multimodal: list = field(default_factory=lambda: ["text"])
    name: Optional[str] = None
    output: list = field(default_factory=lambda: ["text"])
    provider: str = "openai"
    reasoning_effort: bool = False
    tokens: int = 0
    tool_calls: bool = False

    def __init__(self, id: Optional[str] = None):
        """
        Model data item

        :param id: Model ID
        """
        self.ctx = 0
        self.custom_api_endpoint = ""
        self.custom_api_key = ""
        self.default = False
        self.extra = {}
        self.id = id
        self.imported = False
        self.is_hidden = False
        self.input = ["text"]  # multimodal support: image, audio, etc.
        self.langchain = {}
        self.llama_index = {}
        self.mode = ["chat"]
        self.multimodal = ["text"]  # multimodal support: image, audio, etc.
        self.name = None
        self.output = ["text"]  # multimodal support: image, audio, etc.
        self.provider = "openai"  # default provider
        self.reasoning_effort = False  # allow runtime reasoning-effort selection
        self.tokens = 0
        self.tool_calls = False  # native tool calls available

    def from_dict(self, data: dict):
        """
        Load data from dict

        :param data: dict
        """
        if 'ctx' in data:
            self.ctx = data['ctx']
        if 'custom_api_endpoint' in data:
            self.custom_api_endpoint = data['custom_api_endpoint'] or ""
        if 'custom_api_key' in data:
            self.custom_api_key = data['custom_api_key'] or ""
        if 'default' in data:
            self.default = data['default']
        if 'extra' in data:
            self.extra = data['extra']
        if 'id' in data:
            self.id = data['id']
        if 'imported' in data:
            self.imported = data['imported']
        if 'is_hidden' in data:
            self.is_hidden = data['is_hidden']
        if 'input' in data:
            self.input = self._normalize_list(data['input'])
        if 'mode' in data:
            self.mode = self._normalize_list(data['mode'])
            # Backward compatibility: old models configured only for the
            # removed Chat with Files mode are regular Chat models now.
            # Keep the legacy flag and add Chat so the model becomes visible
            # in Chat immediately and the normalized mode list is persisted
            # on the next regular model save.
            if MODE_LLAMA_INDEX in self.mode and MODE_CHAT not in self.mode:
                self.mode.append(MODE_CHAT)
        if 'name' in data:
            self.name = data['name']
        if 'output' in data:
            self.output = self._normalize_list(data['output'])
        if 'provider' in data:
            self.provider = data['provider']
        if 'reasoning_effort' in data:
            self.reasoning_effort = bool(data['reasoning_effort'])
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

    @staticmethod
    def _normalize_list(value) -> list:
        """
        Normalize model list fields loaded from config/editor values.

        Persisted model definitions use comma-separated strings. Accept a
        list as well for callers that already provide normalized values, but
        keep the editor bool-list contract unchanged.

        :param value: comma-separated string or iterable of values
        :return: normalized list of non-empty strings
        """
        if value is None:
            return []
        if isinstance(value, str):
            values = value.split(',')
        elif isinstance(value, (list, tuple, set)):
            values = value
        else:
            values = [value]

        result = []
        for item in values:
            if item is None:
                continue
            item = str(item).strip()
            if item:
                result.append(item)
        return result

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
            'custom_api_endpoint': self.custom_api_endpoint,
            'custom_api_key': self.custom_api_key,
            'tokens': self.tokens,
            'default': self.default,
            'extra': self.extra,
            'imported': self.imported,
            'is_hidden': self.is_hidden,
            'provider': self.provider,
            'reasoning_effort': self.reasoning_effort,
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
        Check if model supports a user-facing mode.

        Transport/backend support is resolved separately by Bridge.  In
        particular, Chat is no longer synonymous with the OpenAI-compatible
        API transport.  ``llama_index`` in old model configs is kept only as a
        backward-compatible alias for Chat.

        :param mode: Mode
        :return: True if supported
        """
        if mode == MODE_CHAT:
            return MODE_CHAT in self.mode or MODE_LLAMA_INDEX in self.mode
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
        return (self.provider in OPENAI_COMPATIBLE_PROVIDERS
                or (isinstance(self.provider, str) and self.provider.startswith("custom_")))

    def is_gpt(self) -> bool:
        """
        Check if model is supported by OpenAI Responses API

        :return: True if OpenAI Responses API compatible
        """
        if self.provider not in ("openai", "azure_openai"):
            return False

        if self.id.startswith("gpt-oss"):
            return False

        if (self.id.startswith("gpt-")
                or self.id.startswith("chatgpt")
                or is_openai_o_series(self.id)
                or self.id.startswith("codex-")
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
        Get Ollama model ID (name used for ollama pull / API).

        :return: model ID, or self.id when no "model" arg is set (e.g. custom/non-default list)
        """
        if "args" in self.llama_index:
            for arg in self.llama_index["args"]:
                if arg["name"] == "model" and arg.get("value"):
                    return (arg["value"] or "").strip()
        return (self.id or "").strip()

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
        return MULTIMODAL_IMAGE in self.input

    def is_image_output(self) -> bool:
        """
        Check if model supports image output

        :return: True if supports image output
        """
        return MULTIMODAL_IMAGE in self.output or MODE_VISION in self.mode

    def is_audio_input(self) -> bool:
        """
        Check if model supports audio input

        :return: True if supports audio input
        """
        return MULTIMODAL_AUDIO in self.input

    def is_audio_output(self) -> bool:
        """
        Check if model supports audio output

        :return: True if supports audio output
        """
        return MULTIMODAL_AUDIO in self.output

    def is_video_input(self) -> bool:
        """
        Check if model supports video input

        :return: True if supports video input
        """
        return MULTIMODAL_VIDEO in self.input

    def is_video_output(self) -> bool:
        """
        Check if model supports video output

        :return: True if supports video output
        """
        return MULTIMODAL_VIDEO in self.output

    def is_music_output(self) -> bool:
        """
        Check if model supports music output

        :return: True if supports music output
        """
        return MULTIMODAL_AUDIO in self.output

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