#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.22 02:00:00                  #
# ================================================== #

import copy

from pygpt_net.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Model editor controller

        :param window: Window instance
        """
        self.window = window
        self.dialog = False
        self.config_initialized = False
        self.current = None
        self.width = 800
        self.height = 500
        self.options = {
            "id": {
                "type": "text",
                "label": "model.id",
            },
            "name": {
                "type": "text",
                "label": "model.name",
            },
            "ctx": {
                "type": "int",
                "label": "model.ctx",
                "description": "model.ctx.desc",
            },
            "tokens": {
                "type": "int",
                "label": "model.tokens",
                "description": "model.tokens.desc",
            },
            "mode": {
                "type": "text",  # list of comma separated values
                "label": "model.mode",
                "description": "model.mode.desc",
            },
            "default": {
                "type": "bool",
                "label": "model.default",
            },
            "langchain.provider": {
                "type": "combo",
                "use": "langchain_providers",
                "label": "model.langchain.provider",
                "description": "model.langchain.provider.desc",
            },
            "langchain.mode": {
                "type": "text",  # list of comma separated values
                "label": "model.langchain.mode",
                "description": "model.langchain.mode.desc",
            },
            "langchain.args": {
                "type": "dict",
                "keys": {
                    'name': 'text',
                    'value': 'text',
                    'type': {
                        "type": "combo",
                        "use": "var_types",
                    },
                },
                "label": "model.langchain.args",
                "description": "model.langchain.args.desc",
                "advanced": True,
            },
            "langchain.env": {
                "type": "dict",
                "keys": {
                    'name': 'text',
                    'value': 'text',
                },
                "label": "model.langchain.env",
                "description": "model.langchain.env.desc",
                "advanced": True,
            },
            "llama_index.provider": {
                "type": "combo",
                "use": "llama_index_providers",
                "label": "model.llama_index.provider",
                "description": "model.llama_index.provider.desc",
            },
            "llama_index.mode": {
                "type": "text",  # list of comma separated values
                "label": "model.llama_index.mode",
                "description": "model.llama_index.mode.desc",
            },
            "llama_index.args": {
                "type": "dict",
                "keys": {
                    'name': 'text',
                    'value': 'text',
                    'type': {
                        "type": "combo",
                        "use": "var_types",
                    },
                },
                "label": "model.llama_index.args",
                "description": "model.llama_index.args.desc",
                "advanced": True,
            },
            "llama_index.env": {
                "type": "dict",
                "keys": {
                    'name': 'text',
                    'value': 'text',
                },
                "label": "model.llama_index.env",
                "description": "model.llama_index.env.desc",
                "advanced": True,
            },
        }

    def get_options(self):
        """
        Get options list

        :return: options list
        """
        return self.options

    def get_option(self, key: str):
        """
        Get option by key

        :param key: option key
        :return: option
        """
        if key in self.options:
            return self.options[key]

    def setup(self):
        """Set up editor"""
        idx = None
        self.window.model_settings.setup(idx)  # widget dialog setup
        parent = "model"
        keys = [
            "langchain.args",
            "langchain.env",
        ]
        for key in keys:
            self.window.ui.dialogs.register_dictionary(
                key,
                parent,
                self.get_option(key),
            )

    def toggle_editor(self):
        """Toggle models editor dialog"""
        if self.dialog:
            self.close()
        else:
            self.open()

    def open(self, force: bool = False):
        """
        Open models editor dialog

        :param force: force open dialog
        """
        if not self.config_initialized:
            self.setup()
            self.config_initialized = True
        if not self.dialog or force:
            self.init()
            self.window.ui.dialogs.open(
                "models.editor",
                width=self.width,
                height=self.height,
            )
            self.dialog = True

    def close(self):
        """Close models editor dialog"""
        if self.dialog:
            self.window.ui.dialogs.close('models.editor')
            self.dialog = False

    def init(self):
        """Initialize models editor options"""
        self.reload_items()

        # select the first plugin on list if no plugin selected yet
        if self.current is None:
            if len(self.window.core.models.items) > 0:
                self.current = list(self.window.core.models.items.keys())[0]

        # assign plugins options to config dialog fields
        options = copy.deepcopy(self.get_options())  # copy options
        model = self.window.core.models.items[self.current]
        data_dict = model.to_dict()
        for key in options:
            value = data_dict[key]
            options[key]["value"] = value

        if self.current is not None:
            self.set_tab_by_id(self.current)

        # load and apply options to config dialog
        self.window.controller.config.load_options("model", options)

    def save(self, persist: bool = True):
        """
        Save models editor

        :param persist: persist to file and close dialog
        """
        options = copy.deepcopy(self.get_options())  # copy options
        data_dict = {}
        for key in options:
            value = self.window.controller.config.get_value(
                parent_id="model",
                key=key,
                option=options[key],
            )
            data_dict[key] = value
        self.window.core.models.items[self.current].from_dict(data_dict)

        # save config
        if persist:
            self.window.core.models.save()
            self.close()
            self.window.ui.status(trans("info.settings.saved"))

    def reload_items(self):
        """Reload items"""
        items = self.window.core.models.items
        self.window.model_settings.update_list("models.list", items)

    def select(self, idx: int):
        """Select model"""
        self.save(persist=False)
        self.current = self.get_model_by_tab_idx(idx)
        self.init()

    def new(self):
        """Create new model"""
        model = self.window.core.models.create_empty()
        self.window.core.models.save()
        self.reload_items()

        # switch to created model
        self.current = model.id
        idx = self.get_tab_by_id(self.current)
        self.set_by_tab(idx)
        self.init()

    def delete_by_idx(self, idx: int, force: bool = False):
        """
        Delete model by idx

        :param idx: model idx
        :param force: force delete
        """
        model = self.get_model_by_tab_idx(idx)
        if not force:
            self.window.ui.dialogs.confirm(
                type="models.editor.delete",
                id=idx,
                msg=trans("dialog.models.editor.delete.confirm"),
            )
            return
        self.window.core.models.delete(model)
        self.window.core.models.save()
        self.reload_items()
        if self.current == model:
            self.current = None
        self.init()

    def load_defaults_user(self, force: bool = False):
        """
        Load models editor user defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type="models.editor.defaults.user",
                id=-1,
                msg=trans("dialog.models.editor.defaults.user.confirm"),
            )
            return

        # reload settings window
        self.window.core.models.save()
        self.current = None
        self.reload_items()
        self.init()
        # self.window.ui.dialogs.alert(trans('dialog.models.editor.defaults.user.result'))

    def load_defaults_app(self, force: bool = False):
        """
        Load models editor app defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type="models.editor.defaults.app",
                id=-1,
                msg=trans("dialog.models.editor.defaults.app.confirm"),
            )
            return

        # restore default models (from app base models)
        self.window.core.models.restore_default()  # all models restore
        self.window.core.models.save()

        # reload settings window
        self.current = None
        self.reload_items()
        self.init()
        self.window.ui.dialogs.alert(
            trans('dialog.models.editor.defaults.app.result')
        )

    def set_by_tab(self, idx: int):
        """
        Set current list by tab index

        :param idx: tab index
        """
        model_idx = 0
        for id in self.window.core.models.get_ids():
            if model_idx == idx:
                self.current = id
                break
            model_idx += 1
        current = self.window.ui.models['models.list'].index(idx, 0)
        self.window.ui.nodes['models.list'].setCurrentIndex(current)

    def set_tab_by_id(self, model_id: str):
        """
        Set current list to model id

        :param model_id: model id
        """
        idx = self.get_tab_idx(model_id)
        current = self.window.ui.models['models.list'].index(idx, 0)
        self.window.ui.nodes['models.list'].setCurrentIndex(current)

    def get_tab_idx(self, model_id: str) -> int:
        """
        Get model list index

        :param model_id: model id
        :return: list index
        """
        model_idx = None
        i = 0
        for id in self.window.core.models.get_ids():
            if id == model_id:
                model_idx = i
                break
            i += 1
        return model_idx

    def get_tab_by_id(self, model_id: str) -> int:
        """
        Get model list index

        :param model_id: model id
        :return: list index
        """
        model_idx = None
        i = 0
        for id in self.window.core.models.get_ids():
            if id == model_id:
                model_idx = i
                break
            i += 1
        return model_idx

    def get_model_by_tab_idx(self, idx: int) -> str or None:
        """
        Get model key by list index

        :param idx: list index
        :return: model key
        """
        model_idx = 0
        for id in self.window.core.models.get_ids():
            if model_idx == idx:
                return id
            model_idx += 1
        return None

    def open_by_idx(self, idx: int):
        """
        Open models editor by tab index (RMB "edit" on global models list)

        :param idx: list index
        """
        mode = self.window.core.config.get('mode')
        model = self.window.core.models.get_by_idx(idx, mode)
        if model is None:
            return
        self.current = model
        self.open(force=True)
