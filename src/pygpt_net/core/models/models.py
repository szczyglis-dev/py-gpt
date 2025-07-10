#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.09 22:00:00                  #
# ================================================== #

import copy
from typing import Optional, List, Dict

from packaging.version import Version

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_RESEARCH,
    MULTIMODAL_TEXT,
    MULTIMODAL_IMAGE,
    MULTIMODAL_AUDIO,
    MULTIMODAL_VIDEO,
)
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.core.model.json_file import JsonFileProvider

from .ollama import Ollama

class Models:
    def __init__(self, window=None):
        """
        Models core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.ollama = Ollama(window)
        self.default = "gpt-4o-mini"
        self.items = {}
        self.multimodal = [
            MULTIMODAL_TEXT,
            MULTIMODAL_IMAGE,
            MULTIMODAL_AUDIO,
            MULTIMODAL_VIDEO,
        ]

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        return self.provider.patch(app_version)

    def patch_missing(self) -> bool:
        """
        Patch missing models

        :return: True if models were patched
        """
        base_items = self.get_base()
        updated = False
        added_keys = []

        # check for missing keys
        for key in base_items:
            if key not in self.items:
                self.items[key] = copy.deepcopy(base_items[key])
                updated = True

        # check for missing models ids
        for key in base_items:
            model_id = base_items[key].id
            old_exists = False
            for old_key in self.items:
                if self.items[old_key].id == model_id:
                    old_exists = True
                    break
            if not old_exists and key not in added_keys:
                self.items[key] = copy.deepcopy(base_items[key])
                added_keys.append(key)
                updated = True

        # update multimodal options
        for key in self.items:
            if key in base_items:
                if base_items[key].input != self.items[key].input:
                    self.items[key].input = base_items[key].input
                    updated = True
                if base_items[key].output != self.items[key].output:
                    self.items[key].output = base_items[key].output
                    updated = True

        # update empty multimodal options
        for key in self.items:
            if isinstance(self.items[key].input, list):
                if len(self.items[key].input) == 0:
                    self.items[key].input = ["text"]
                    updated = True
            if isinstance(self.items[key].output, list):
                if len(self.items[key].output) == 0:
                    self.items[key].output = ["text"]
                    updated = True

        if updated:
            self.save()

        return updated

    def get(self, key: str) -> ModelItem:
        """
        Return model config

        :param key: model name
        :return: model config object
        """
        if key in self.items:
            return self.items[key]

    def get_ids(self) -> List[str]:
        """
        Return models ids

        :return: model ids list
        """
        return list(self.items.keys())

    def get_id_by_idx_all(self, idx: int) -> str:
        """
        Return model id by index

        :param idx: model idx
        :return: model id
        """
        return list(self.items.keys())[idx]

    def has(self, model: str) -> bool:
        """
        Check if model exists

        :param model: model name
        :return: True if model exists
        """
        return model in self.items

    def is_allowed(
            self,
            model: str,
            mode: str
    ) -> bool:
        """
        Check if model is allowed for mode

        :param model: model name
        :param mode: mode name
        :return: True if model is allowed for mode
        """
        if model in self.items:
            return mode in self.items[model].mode
        return False

    def get_id(
            self,
            key: str
    ) -> str:
        """
        Return model internal ID

        :param key: model key
        :return: model id
        """
        if key in self.items:
            return self.items[key].id

    def get_by_idx(
            self,
            idx: int,
            mode: str
    ) -> str:
        """
        Return model by index

        :param idx: model idx
        :param mode: mode name
        :return: model name
        """
        items = self.get_by_mode(mode)
        return list(items.keys())[idx]

    def get_by_mode(
            self,
            mode: str
    ) -> Dict[str, ModelItem]:
        """
        Return models for mode

        :param mode: mode name
        :return: models dict for mode
        """
        items = {}
        for key in self.items:
            if mode in self.items[key].mode:
                items[key] = self.items[key]
        return items

    def get_next(
            self,
            model: str,
            mode: str
    ) -> str:
        """
        Return next model

        :param model: current model
        :param mode: mode name
        :return: next model
        """
        items = self.get_by_mode(mode)
        keys = list(items.keys())
        idx = keys.index(model)
        if idx + 1 < len(keys):
            return keys[idx + 1]
        return keys[0]

    def get_prev(
            self,
            model: str,
            mode: str
    ) -> str:
        """
        Return previous model

        :param model: current model
        :param mode: mode name
        :return: previous model
        """
        items = self.get_by_mode(mode)
        keys = list(items.keys())
        idx = keys.index(model)
        if idx - 1 >= 0:
            return keys[idx - 1]
        return keys[-1]

    def create_id(self):
        """
        Create new model id

        :return: new model id
        """
        id = "model-000"
        while id in self.items:
            id = "model-" + str(int(id.split("-")[1]) + 1).zfill(3)
        return id

    def get_multimodal_list(self) -> List[str]:
        """
        Return available multimodal types

        :return: list of multimodal types
        """
        return self.multimodal

    def create_empty(self, append: bool = True) -> ModelItem:
        """
        Create new empty model

        :param append: if True, append model to items
        :return: new model

        """
        id = self.create_id()
        model = ModelItem()
        model.id = id
        model.name = "New model"
        if append:
            self.items[id] = model
        return model

    def get_all(self) -> Dict[str, ModelItem]:
        """
        Return all models

        :return: all models
        """
        return self.items

    def from_defaults(self) -> ModelItem:
        """
        Create default model

        :return: new model
        """
        model = ModelItem()
        model.id = self.default
        model.name = self.default
        model.tokens = 4096
        model.ctx = 128000
        model.input = ["text"]
        model.output = ["text"]
        model.provider = "openai"
        model.mode = ["chat"]
        return model

    def delete(self, model: str):
        """
        Delete model

        :param model: model name
        """
        if model in self.items:
            del self.items[model]

    def has_model(
            self,
            mode: str,
            model: str
    ) -> bool:
        """
        Check if model exists for mode

        :param mode: mode name
        :param model: model name
        :return: True if model exists for mode
        """
        items = self.get_by_mode(mode)
        return model in items

    def get_default(self, mode: str) -> Optional[str]:
        """
        Return default model for mode

        :param mode: mode name
        :return: default model name
        """
        models = {}
        items = self.get_by_mode(mode)
        for k in items:
            models[k] = items[k]
        if len(models) == 0:
            return None
        return list(models.keys())[0]

    def get_tokens(self, model: str) -> int:
        """
        Return model tokens

        :param model: model name
        :return: number of tokens
        """
        if model in self.items:
            return self.items[model].tokens
        return 1

    def get_num_ctx(self, model: str) -> int:
        """
        Return model context window tokens

        :param model: model name
        :return: number of ctx tokens
        """
        if model in self.items:
            return self.items[model].ctx
        return 4096

    def restore_default(
            self,
            model: Optional[str] = None
    ):
        """
        Restore default models

        :param model: model name
        """
        # restore all models
        if model is None:
            self.load_base()
            return

        # restore single model
        items = self.provider.load_base()
        if model in items:
            self.items[model] = items[model]

    def get_base(self) -> Dict[str, ModelItem]:
        """
        Get base models

        :return: base models
        """
        return self.provider.load_base()

    def load_base(self):
        """Load models base"""
        self.items = self.get_base()
        self.sort_items()

    def load(self):
        """Load models"""
        self.items = self.provider.load()
        self.sort_items()

    def sort_items(self):
        """Sort items"""
        if self.items:
            self.items = dict(sorted(self.items.items(), key=lambda x: x[1].name.lower()))

    def save(self):
        """Save models"""
        self.provider.save(self.items)

    def get_supported_mode(
            self,
            model: ModelItem,
            mode: str
    ) -> str:
        """
        Get supported mode

        :param model: ModelItem
        :param mode: mode (initial)
        :return: mode (supported)
        """
        prev_mode = mode
        # if OpenAI API model and not llama_index mode, switch to Chat mode
        if model.is_supported(MODE_CHAT) and mode != MODE_LLAMA_INDEX:  # do not switch if llama_index mode!
            if prev_mode != MODE_CHAT:
                self.window.core.debug.info(
                    "WARNING: Switching to chat mode (model not supported in: {})".format(prev_mode))
            return MODE_CHAT

        # Research / Perplexity
        if model.is_supported(MODE_RESEARCH):
            if prev_mode != MODE_RESEARCH:
                self.window.core.debug.info(
                    "WARNING: Switching to research mode (model not supported in: {})".format(mode))
            mode = MODE_RESEARCH

        # Llama Index / Chat with Files
        elif model.is_supported(MODE_LLAMA_INDEX):
            if prev_mode != MODE_LLAMA_INDEX:
                self.window.core.debug.info(
                    "WARNING: Switching to llama_index mode (model not supported in: {})".format(mode))
            mode = MODE_LLAMA_INDEX

        # LangChain
        """
        elif model.is_supported(MODE_LANGCHAIN):
            self.window.core.debug.info(
                "WARNING: Switching to langchain mode (model not supported in: {})".format(mode))
            mode = MODE_LANGCHAIN
        """
        return mode

    def prepare_client_args(
            self,
            args: dict,
            mode: str = MODE_CHAT,
            model: ModelItem = None
    ) -> Dict[str, str]:
        """
        Prepare chat client arguments

        :param args: client arguments
        :param mode: mode name
        :param model: ModelItem
        :return: client arguments dict
        """
        # research mode endpoint - Perplexity
        if model is not None:
            # xAI / grok
            if model.provider == "x_ai":
                args["api_key"] = self.window.core.config.get('api_key_xai', "")
                args["base_url"] = self.window.core.config.get('api_endpoint_xai', "")
                self.window.core.debug.info("[api] Using client: xAI")
            # Perplexity
            elif model.provider == "perplexity":
                args["api_key"] = self.window.core.config.get('api_key_perplexity', "")
                args["base_url"] = self.window.core.config.get('api_endpoint_perplexity', "")
                self.window.core.debug.info("[api] Using client: Perplexity")
            # Google
            elif model.provider == "google":
                args["api_key"] = self.window.core.config.get('api_key_google', "")
                args["base_url"] = self.window.core.config.get('api_endpoint_google', "")
                self.window.core.debug.info("[api] Using client: Google")
            # Anthropic
            elif model.provider == "anthropic":
                args["api_key"] = self.window.core.config.get('api_key_anthropic', "")
                args["base_url"] = self.window.core.config.get('api_endpoint_anthropic', "")
                self.window.core.debug.info("[api] Using client: Anthropic")
            # Deepseek
            elif model.provider == "deepseek_api":
                args["api_key"] = self.window.core.config.get('api_key_deepseek', "")
                args["base_url"] = self.window.core.config.get('api_endpoint_deepseek', "")
                self.window.core.debug.info("[api] Using client: Deepseek API")
            # Mistral AI
            elif model.provider == "mistral_ai":
                args["api_key"] = self.window.core.config.get('api_key_mistral', "")
                args["base_url"] = self.window.core.config.get('api_endpoint_mistral', "")
                self.window.core.debug.info("[api] Using client: Mistral AI API")
            else:
                self.window.core.debug.info("[api] Using client: OpenAI (default)")

            # do not include organization for non-OpenAI providers
            if model.provider != "openai":
                if "organization" in args:
                    del args["organization"]
        else:
            self.window.core.debug.info("[api] No model provided, using default OpenAI client")
        return args

    def is_tool_call_allowed(self, mode: str, model: ModelItem) -> bool:
        """
        Check if native tool call is allowed for model and mode

        :param mode: Mode name
        :param model: ModelItem
        :return: True if tool call is allowed, False otherwise
        """
        if self.window.core.config.get("llama.idx.react", False):
            return True # allow all for ReAct agent

        stream = self.window.core.config.get("stream", False)
        not_allowed_providers = [
            "ollama",
            "hugging_face_api",
            "deepseek_api",
            "perplexity",
            # "x_ai",
        ]
        if mode == MODE_LLAMA_INDEX:
            if model.provider == "google" and stream:
                not_allowed_providers.append("google")
        if model.provider in not_allowed_providers:
            return False
        return True

    def get_version(self) -> str:
        """
        Get config version

        :return: config version
        """
        return self.provider.get_version()
