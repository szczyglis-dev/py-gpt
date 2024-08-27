#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 16:00:00                  #
# ================================================== #

import copy

from packaging.version import Version

from pygpt_net.item.model import ModelItem
from pygpt_net.provider.core.model.json_file import JsonFileProvider


class Models:
    def __init__(self, window=None):
        """
        Models core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.items = {}

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

    def get_ids(self) -> list:
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

    def is_allowed(self, model: str, mode: str) -> bool:
        """
        Check if model is allowed for mode

        :param model: model name
        :param mode: mode name
        :return: True if model is allowed for mode
        """
        if model in self.items:
            return mode in self.items[model].mode
        return False

    def get_id(self, key: str) -> str:
        """
        Return model internal ID

        :param key: model key
        :return: model id
        """
        if key in self.items:
            return self.items[key].id

    def get_by_idx(self, idx: int, mode: str) -> str:
        """
        Return model by index

        :param idx: model idx
        :param mode: mode name
        :return: model name
        """
        items = self.get_by_mode(mode)
        return list(items.keys())[idx]

    def get_by_mode(self, mode: str) -> dict:
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

    def create_id(self):
        """
        Create new model id

        :return: new model id
        """
        id = "model-000"
        while id in self.items:
            id = "model-" + str(int(id.split("-")[1]) + 1).zfill(3)
        return id

    def create_empty(self) -> ModelItem:
        """
        Create new empty model

        :return: new model
        """
        id = self.create_id()
        model = ModelItem()
        model.id = id
        model.name = "New model"
        self.items[id] = model
        return model

    def get_all(self) -> dict:
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
        model.id = "gpt-3.5-turbo-1106"
        model.name = "gpt-3.5-turbo-1106"
        model.tokens = 4096
        model.ctx = 4096
        return model

    def delete(self, model: str):
        """
        Delete model

        :param model: model name
        """
        if model in self.items:
            del self.items[model]

    def has_model(self, mode: str, model: str) -> bool:
        """
        Check if model exists for mode

        :param mode: mode name
        :param model: model name
        :return: True if model exists for mode
        """
        items = self.get_by_mode(mode)
        return model in items

    def get_default(self, mode: str) -> str | None:
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

    def restore_default(self, model: str = None):
        """Restore default models"""
        # restore all models
        if model is None:
            self.load_base()
            return

        # restore single model
        items = self.provider.load_base()
        if model in items:
            self.items[model] = items[model]

    def get_base(self) -> dict:
        """Get base models"""
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
        self.items = dict(sorted(self.items.items(), key=lambda item: item[0]))

    def save(self):
        """Save models"""
        self.provider.save(self.items)

    def get_supported_mode(self, model: ModelItem, mode: str) -> str:
        """
        Get supported mode

        :param model: ModelItem
        :param mode: mode (initial)
        :return: mode (supported)
        """
        if model.is_supported("chat"):
            self.window.core.debug.info(
                "WARNING: Switching to chat mode (model not supported in: {})".format(mode))
            mode = "chat"
        elif model.is_supported("llama_index"):
            self.window.core.debug.info(
                "WARNING: Switching to llama_index mode (model not supported in: {})".format(mode))
            mode = "llama_index"
        elif model.is_supported("langchain"):
            self.window.core.debug.info(
                "WARNING: Switching to langchain mode (model not supported in: {})".format(mode))
            mode = "langchain"
        return mode

    def get_version(self) -> str:
        """Get config version"""
        return self.provider.get_version()
