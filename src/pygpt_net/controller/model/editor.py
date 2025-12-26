#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.26 20:00:00                  #
# ================================================== #

import copy
import json
from typing import Optional, Any

from pygpt_net.core.events import Event
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
        self.previous = None  # previous models
        self.width = 800
        self.height = 500
        self.selected = []
        self.locked = False
        self.provider = "-" # all providers by default
        self.options = {
            "id": {
                "type": "text",
                "label": "model.id",
                "description": "model.id.desc",
            },
            "name": {
                "type": "text",
                "label": "model.name",
                "description": "model.name.desc",
            },
            "provider": {
                "type": "combo",
                "use": "llm_providers",
                "label": "model.provider",
                "description": "model.provider.desc",
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
                "type": "bool_list",  # list of comma separated values
                "label": "model.mode",
                "use": "modes",
            },
            "tool_calls": {
                "type": "bool",
                "label": "model.tool_calls",
                "description": "model.tool_calls.desc",
            },
            "input": {
                "type": "bool_list",  # list of comma separated values
                "label": "model.input",
                "use": "multimodal",
                "advanced": True,
            },
            "output": {
                "type": "bool_list",  # list of comma separated values
                "label": "model.output",
                "use": "multimodal",
                "advanced": True,
            },
            "default": {
                "type": "bool",
                "label": "model.default",
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
            "extra_json": {
                "type": "textarea",
                "label": "model.extra",
                "description": "model.extra.desc",
                "advanced": True,
            },
        }
        self.custom_fields = ["extra_json"]

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

    def get_provider_option(self) -> dict:
        """
        Get provider option

        :return: provider option
        """
        return {
            "type": "combo",
            "use": "llm_providers",
            "label": "model.provider",
            "description": "model.provider.desc",
        }

    def setup(self):
        """Set up editor"""
        idx = None
        self.window.model_settings.setup(idx)  # widget dialog setup
        self.window.ui.add_hook("update.model.name", self.hook_update)
        self.window.ui.add_hook("update.model.mode", self.hook_update)
        self.update_provider(self.provider)
        self.window.ui.add_hook("update.model.provider_global", self.hook_update)

    def update_provider(self, provider: str):
        """
        Set provider

        :param provider: provider name
        """
        self.window.controller.config.apply_value(
            parent_id="model",
            key="provider_global",
            option=self.get_provider_option(),
            value=provider,
        )

    def hook_update(
            self,
            key: str,
            value: Any,
            caller,
            *args,
            **kwargs
    ):
        """
        Hook: on settings update

        :param key: config key
        :param value: config value
        :param caller: caller name
        :param args: args
        :param kwargs: kwargs
        """
        if self.window.controller.reloading or self.locked:
            return  # ignore hooks during reloading process

        if key == "provider_global":
            # update provider option dynamically
            if self.provider == value:
                return
            self.save(persist=False)
            self.locked = True
            self.current = None
            self.provider = value
            self.reload_items()
            if self.current is None:
                self.init()
            self.locked = False
            return

        if key in ["id", "name", "mode"]:
            self.save(persist=False)
            self.reload_items()
            # select by current model
            idx = self.get_tab_by_id(self.current)
            if idx is not None:
                self.set_by_tab(idx)

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
        self.locked = True
        if not self.config_initialized:
            self.setup()
            self.config_initialized = True
        if not self.dialog or force:
            self.current = None
            self.init()
            self.previous = copy.deepcopy(self.window.core.models.items)
            self.window.ui.dialogs.open(
                "models.editor",
                width=self.width,
                height=self.height,
            )
            self.dialog = True
            if "models.editor.search" in self.window.ui.nodes:
                self.window.ui.nodes['models.editor.search'].setFocus()  # focus on search
        self.locked = False

    def undo(self):
        """Undo last changes in models editor"""
        if self.previous is not None:
            self.locked = True
            self.window.core.models.items = copy.deepcopy(self.previous)
            self.window.core.models.save()
            self.reload_items()
            self.init()
            self.locked = False

    def close(self):
        """Close models editor dialog"""
        if self.dialog:
            self.window.ui.dialogs.close('models.editor')
            self.dialog = False

    def init(self):
        """Initialize models editor options"""
        self.window.core.models.sort_items()
        self.reload_items()

        # select the first model on list if no model selected yet
        items = self.prepare_items()
        if self.current is None:
            if len(items) > 0:
                self.current = list(items.keys())[0]

        # assign model options to config dialog fields
        options = copy.deepcopy(self.get_options())  # copy options
        if self.current in items:
            model = items[self.current]
            data_dict = model.to_dict()
            for key in options:
                if key in data_dict:
                    value = data_dict[key]
                    options[key]["value"] = value

            # custom fields
            options["extra_json"]["value"] = json.dumps(model.extra, indent=4) if model.extra else ""

        if self.current is not None and self.current in items:
            self.set_tab_by_id(self.current)

        # load and apply options to config dialog
        self.window.controller.config.load_options("model", options)

    def save(
            self,
            persist: bool = True,
            force: bool = False
    ):
        """
        Save models editor

        :param persist: persist to file and close dialog
        :param force: force save without validation
        """
        options = copy.deepcopy(self.get_options())  # copy options
        data_dict = {}

        # base fields
        for key in options:
            if key in self.custom_fields:
                continue
            value = self.window.controller.config.get_value(
                parent_id="model",
                key=key,
                option=options[key],
            )
            data_dict[key] = value

        # custom fields
        if "extra_json" in options:
            extra_json = self.window.controller.config.get_value(
                parent_id="model",
                key="extra_json",
                option=options["extra_json"],
            )
            try:
                if extra_json:
                    decoded = json.loads(extra_json)
                    data_dict["extra"] = decoded
                else:
                    data_dict["extra"] = {}
            except json.JSONDecodeError as error:
                self.window.ui.dialogs.alert(
                    "JSON decoding error in 'extra' field. Please check the syntax:\n\n{}".format(error)
                )
                if not force:
                    return # if JSON is invalid, do not save

        # update current model
        if self.current in self.window.core.models.items:
            self.window.core.models.items[self.current].from_dict(data_dict)
            if persist:
                # change key to model ID if key not exists
                old_key = self.current
                new_key = self.window.core.models.items[self.current].id
                if old_key != new_key:
                    if new_key not in self.window.core.models.items:
                        self.window.core.models.items[new_key] = self.window.core.models.items.pop(old_key)
                        self.current = new_key  # switch current key

        # save config
        if persist:
            self.window.core.models.save()
            self.close()
            self.window.update_status(trans("info.settings.saved"))

        self.window.core.models.sort_items()
        self.window.controller.model.reload()

        # dispatch on update event
        event = Event(Event.MODELS_CHANGED)
        self.window.dispatch(event, all=True)

    def prepare_items(self) -> dict:
        """
        Prepare items by provider

        :return: items by provider
        """
        items = self.window.core.models.items
        if self.provider == "-":
            return items # all providers
        items_by_provider = {}
        for model_id, model in items.items():
            provider = model.provider
            if provider != self.provider:
                continue
            items_by_provider[model_id] = model
        return items_by_provider

    def reload_items(self):
        """Reload items"""
        self.window.model_settings.update_list("models.list", self.prepare_items())

    def select(self, idx: int):
        """Select model"""
        self.locked = True
        self.save(persist=False)
        self.current = self.get_model_by_tab_idx(idx)
        self.init()
        self.locked = False

    def new(self):
        """Create new model"""
        self.locked = True
        self.save(persist=False)
        model, new_id = self.window.core.models.create_empty()
        if self.provider != "-":
            model.provider = self.provider
        self.window.core.models.sort_items()
        self.window.core.models.save()
        self.reload_items()

        # switch to created model
        self.current = model.id
        idx = self.get_tab_by_id(self.current)
        self.set_by_tab(idx)
        self.init()
        self.locked = False

    def delete_by_idx(
            self,
            idx: int,
            force: bool = False
    ):
        """
        Delete model by idx

        :param idx: model idx
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type="models.editor.delete",
                id=idx,
                msg=trans("dialog.models.editor.delete.confirm"),
            )
            return
        self.locked = True
        model = self.get_model_by_tab_idx(idx)
        self.window.core.models.delete(model)
        self.window.core.models.save()
        self.reload_items()
        if self.current == model:
            self.current = None

        # switch to previous model if available
        items = self.prepare_items()
        if len(items) > 0:
            model = self.get_model_by_tab_idx(idx - 1)
            if model:
                self.current = model

        self.init()
        self.locked = False

    def duplicate_by_idx(
            self,
            idx: int
    ):
        """
        Duplicate model by idx

        :param idx: model idx
        """
        self.locked = True
        self.save(persist=False)
        model = self.get_model_by_tab_idx(idx)
        if model:
            new_model, new_id = self.window.core.models.create_empty()
            new_model.from_dict(self.window.core.models.items[model].to_dict())
            new_model.name += " (Copy)"
            self.window.core.models.sort_items()
            self.window.core.models.save()
            self.reload_items()

            # switch to created model
            self.current = new_id
            idx = self.get_tab_by_id(self.current)
            self.set_by_tab(idx)
            self.init()
        self.locked = False

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

        self.undo()

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

        self.locked = True
        # restore default models (from app base models)
        self.window.core.models.restore_default()  # all models restore
        self.window.core.models.save()

        # reload settings window
        self.current = None
        self.window.core.models.sort_items()
        self.reload_items()
        self.init()
        self.window.ui.dialogs.alert(
            trans('dialog.models.editor.defaults.app.result')
        )
        self.previous = copy.deepcopy(self.window.core.models.items)
        self.locked = False

    def set_by_tab(self, idx: int):
        """
        Set current list by tab index

        :param idx: tab index
        """
        if idx is None:
            return
        # Resolve model id using the filtered view mapping
        model_id = self.window.model_settings.get_model_id_by_row(idx)
        if model_id is not None:
            self.current = model_id
            current = self.window.ui.models['models.list'].index(idx, 0)
            self.window.ui.nodes['models.list'].setCurrentIndex(current)

    def set_tab_by_id(self, model_id: str):
        """
        Set current list to model id

        :param model_id: model id
        """
        idx = self.get_tab_idx(model_id)
        if idx is None:
            return
        current = self.window.ui.models['models.list'].index(idx, 0)
        self.window.ui.nodes['models.list'].setCurrentIndex(current)

    def get_tab_idx(self, model_id: str) -> Optional[int]:
        """
        Get model list index (in the current filtered view)

        :param model_id: model id
        :return: list index
        """
        return self.window.model_settings.get_row_by_model_id(model_id)

    def get_tab_by_id(self, model_id: str) -> Optional[int]:
        """
        Get model list index (alias to get_tab_idx for compatibility)

        :param model_id: model id
        :return: list index
        """
        return self.get_tab_idx(model_id)

    def get_model_by_tab_idx(self, idx: int) -> Optional[str]:
        """
        Get model key by list index (in the current filtered view)

        :param idx: list index
        :return: model key
        """
        return self.window.model_settings.get_model_id_by_row(idx)

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

    def add_selected(self, id: int):
        """
        Add selection ID to selected list

        :param id: model ID
        """
        if id not in self.selected:
            self.selected.append(id)

    def remove_selected(self, id: int):
        """
        Remove selection ID from selected list

        :param id: model ID
        """
        if id in self.selected:
            self.selected.remove(id)

    def set_selected(self, id: int):
        """
        Set selected ID in selected list

        :param id: model ID
        """
        self.selected = [id] if id is not None else []

    def clear_selected(self):
        """Clear selected list"""
        self.selected = []