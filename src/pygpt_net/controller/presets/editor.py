#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #

import datetime
import os

from pygpt_net.item.preset import PresetItem
from pygpt_net.utils import trans
from .experts import Experts


class Editor:
    def __init__(self, window=None):
        """
        Presets editor controller

        :param window: Window instance
        """
        self.window = window
        self.experts = Experts(window)
        self.options = {
            "filename": {
                "type": "text",
                "label": "preset.filename",
            },
            "name": {
                "type": "text",
                "label": "preset.name",
            },
            "ai_name": {
                "type": "text",
                "label": "preset.ai_name",
            },
            "user_name": {
                "type": "text",
                "label": "preset.user_name",
            },
            "img": {
                "type": "bool",
                "label": "preset.img",
            },
            "chat": {
                "type": "bool",
                "label": "preset.chat",
            },
            "completion": {
                "type": "bool",
                "label": "preset.completion",
            },
            "vision": {
                "type": "bool",
                "label": "preset.vision",
            },
            "langchain": {
                "type": "bool",
                "label": "preset.langchain",
            },
            "expert": {
                "type": "bool",
                "label": "preset.expert",
            },
            "agent": {
                "type": "bool",
                "label": "preset.agent",
            },
            # "assistant": {
            # "type": "bool",
            # "label": "preset.assistant",
            # },
            "llama_index": {
                "type": "bool",
                "label": "preset.llama_index",
            },
            "model": {
                "label": "toolbox.model.label",
                "type": "combo",
                "use": "models",
                "keys": [],
            },
            "temperature": {
                "type": "float",
                "slider": True,
                "label": "preset.temperature",
                "min": 0,
                "max": 2,
                "step": 1,
                "multiplier": 100,
            },
            "prompt": {
                "type": "textarea",
                "label": "preset.prompt",
                "context_options": ["prompt.template.paste"],
            },
            "tool.function": {
                "type": "dict",
                "label": "preset.tool.function",
                "keys": {
                    'name': 'text',
                    'params': 'textarea',
                    'desc': 'textarea',
                },
                "extra": {
                    "urls": {
                        "Help": "https://platform.openai.com/docs/guides/function-calling",
                    },
                },
            },
        }
        self.id = "preset"
        self.current = None

    def get_options(self) -> dict:
        """
        Get preset options

        :return: preset options
        """
        return self.options

    def get_option(self, id: str) -> dict:
        """
        Get preset option

        :param id: option id
        :return: preset option
        """
        return self.options[id]

    def setup(self):
        """
        Setup preset editor
        """
        # add hooks for config update in real-time
        self.window.ui.add_hook("update.preset.prompt", self.hook_update)

        # register functions dictionary
        parent = "preset"
        key = "tool.function"
        self.window.ui.dialogs.register_dictionary(
            key,
            parent,
            self.get_option(key),
        )

    def hook_update(self, key, value, caller, *args, **kwargs):
        """
        Hook: on settings update in real-time (prompt)
        """
        mode = self.window.core.config.get('mode')
        if key == "prompt":
            self.window.core.config.set('prompt', value)
            if mode == 'assistant':
                self.window.controller.assistant.from_global()  # update current assistant, never called!!!!!
            else:
                self.window.controller.presets.from_global()  # update current preset


    def edit(self, idx: int = None):
        """
        Open preset editor

        :param idx: preset index (row index)
        """
        preset = None
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset = self.window.core.presets.get_by_idx(idx, mode)
        self.init(preset)
        self.window.ui.dialogs.open_editor('editor.preset.presets', idx, width=800)

    def init(self, id: str = None):
        """
        Initialize preset editor

        :param id: preset id (filename)
        """
        data = PresetItem()
        data.name = ""
        data.filename = ""

        if id is not None and id != "":
            if id in self.window.core.presets.items:
                data = self.window.core.presets.items[id]
                data.filename = id
                self.current = data.uuid

        if data.name is None:
            data.name = ""
        if data.ai_name is None:
            data.ai_name = ""
        if data.user_name is None:
            data.user_name = ""
        if data.prompt is None:
            data.prompt = ""
        if data.filename is None:
            data.filename = ""

        # set current mode at start
        if id is None:
            mode = self.window.core.config.get("mode")
            if mode == "chat":
                data.chat = True
            elif mode == "completion":
                data.completion = True
            elif mode == "img":
                data.img = True
            elif mode == "vision":
                data.vision = True
            elif mode == "langchain":
                data.langchain = True
            # elif mode == "'"assistant':
                # data.assistant = True
            elif mode == "llama_index":
                data.llama_index = True
            elif mode == "expert":
                data.expert = True
            elif mode == "agent":
                data.agent = True

        options = {}
        data_dict = data.to_dict()
        for key in self.options:
            options[key] = self.options[key]
            options[key]['value'] = data_dict[key]

        # load options
        self.window.controller.config.load_options(
            self.id,
            options,
        )

        # update experts list, after ID loaded
        self.experts.update_list()

        # restore functions
        if data.has_functions():
            functions = data.get_functions()
            values = []
            for function in functions:
                values.append(
                    {
                        "name": function['name'],
                        "params": function['params'],
                        "desc": function['desc'],
                    }
                )
            self.window.ui.config[self.id]['tool.function'].items = values
            self.window.ui.config[self.id]['tool.function'].model.updateData(values)
        else:
            self.window.ui.config[self.id]['tool.function'].items = []
            self.window.ui.config[self.id]['tool.function'].model.updateData([])

        # set focus to name field
        self.window.ui.config[self.id]['name'].setFocus()

    def save(self, force: bool = False, close: bool = True):
        """
        Save ore create preset

        :param force: force overwrite file
        :param close: close dialog
        """
        id = self.window.controller.config.get_value(
            parent_id=self.id,
            key="filename",
            option=self.options["filename"],
        )
        mode = self.window.core.config.get("mode")
        modes = ["chat", "completion", "img", "vision", "langchain", "llama_index", "expert"]

        # disallow editing default preset
        if id == "current." + mode:
            self.window.ui.dialogs.alert("Reserved ID. Please use another ID.")
            return

        if id is None or id == "":
            name = self.window.controller.config.get_value(
                parent_id=self.id,
                key="name",
                option=self.options["name"],
            )
            if name is None or name == "":
                self.window.ui.dialogs.alert(trans('alert.preset.empty_id'))
                self.window.ui.status(trans('status.preset.empty_id'))
                return

            # generate new filename
            id = self.window.controller.presets.make_filename(name)
            path = os.path.join(
                self.window.core.config.path,
                "presets",
                id + ".json",
            )
            if os.path.exists(path) and not force:
                id = id + '_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        # validate filename
        id = self.window.controller.presets.validate_filename(id)
        if id not in self.window.core.presets.items:
            self.window.core.presets.items[id] = self.window.core.presets.build()
        elif not force:
            self.window.ui.dialogs.confirm(
                type='preset_exists',
                id=id,
                msg=trans('confirm.preset.overwrite'),
            )
            return

        # check if at least one mode is selected
        is_mode = False
        for check in modes:
            if self.window.controller.config.get_value(
                parent_id=self.id,
                key=check,
                option=self.options[check],
            ):
                is_mode = True
                break
        if mode != "agent" and not is_mode:
            self.window.ui.dialogs.alert(
                trans('alert.preset.no_chat_completion')
            )
            return

        # assign data from fields to preset object in items
        self.assign_data(id)

        # if agent, assign experts and select only agent mode
        if self.window.core.config.get('mode') == 'agent':
            self.window.core.presets.items[id].mode = ["agent"]

        # apply changes to current active preset
        current = self.window.core.config.get('preset')
        if current is not None and current == id:
            self.to_current(self.window.core.presets.items[id])
            self.window.core.config.save()

        # update current uuid
        self.current = self.window.core.presets.items[id].uuid

        # save
        self.window.core.presets.save(id)
        self.window.controller.presets.refresh()

        # close dialog
        if close:
            self.window.ui.dialogs.close('editor.preset.presets')
        else:
            # update ID in field
            self.window.controller.config.apply_value(
                parent_id=self.id,
                key="filename",
                option=self.options["filename"],
                value=id,
            )
        self.window.ui.status(trans('status.preset.saved'))

        # sort by name
        self.window.core.presets.sort_by_name()

        # switch to editing preset
        self.window.controller.presets.set(mode, id)

        # update presets list
        self.window.controller.presets.refresh()

    def assign_data(self, id: str):
        """
        Assign data from fields to preset

        :param id: preset id (filename)
        """
        data_dict = {}
        for key in self.options:
            # assigned separately
            if key == "tool.function":
                continue
            data_dict[key] = self.window.controller.config.get_value(
                parent_id=self.id,
                key=key,
                option=self.options[key],
            )
        if data_dict['name'] is None or data_dict['name'] == "":
            data_dict['name'] = id + " " + trans('preset.untitled')
        if data_dict['model'] == '_':
            data_dict['model'] = None

        preset = self.window.core.presets.items[id]
        preset.from_dict(data_dict)
        preset.tools = {
            'function': [],  # functions are assigned separately (below)
        }

        # assign functions tool
        values = self.window.controller.config.get_value(
            parent_id=self.id,
            key='tool.function',
            option=self.options['tool.function'],
        )
        functions = []
        for function in values:
            name = function['name']
            params = function['params']
            desc = function['desc']
            if name is None or name == "":
                continue
            if params is None or params == "":
                params = '{"type": "object", "properties": {}}'  # default empty JSON params
            if desc is None:
                desc = ""
            functions.append(
                {
                    "name": name,
                    "params": params,
                    "desc": desc,
                }
            )

        if len(functions) > 0:
            preset.tools['function'] = functions
        else:
            preset.tools['function'] = []

    def to_current(self, preset: PresetItem):
        """
        Update preset field from editor

        :param preset: preset item
        """
        self.window.core.config.set('ai_name', preset.ai_name)
        self.window.core.config.set('user_name', preset.user_name)
        self.window.core.config.set('prompt', preset.prompt)
        self.window.core.config.set('temperature', preset.temperature)

    def from_current(self):
        """Copy data from current active preset"""
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="ai_name",
            option=self.options["ai_name"],
            value=self.window.core.config.get('ai_name'),
        )
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="user_name",
            option=self.options["user_name"],
            value=self.window.core.config.get('user_name'),
        )
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="prompt",
            option=self.options["prompt"],
            value=self.window.core.config.get('prompt'),
        )
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="temperature",
            option=self.options["temperature"],
            value=self.window.core.config.get('temperature'),
        )
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="model",
            option=self.options["model"],
            value=self.window.core.config.get('model'),
        )

    def update_from_global(self, key, value):
        """Update field from global config"""
        preset_id = self.window.core.config.get('preset')
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.core.presets.items:
                preset = self.window.core.presets.items[preset_id]
                if key == 'preset.user_name':
                    preset.user_name = value
                    self.window.core.config.set('user_name', preset.user_name)
                elif key == 'preset.ai_name':
                    preset.ai_name = value
                    self.window.core.config.set('ai_name', preset.ai_name)
                self.window.core.presets.save(preset_id)
