#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.30 17:00:00                  #
# ================================================== #

import datetime
import os

from pygpt_net.item.preset import PresetItem
from pygpt_net.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Presets editor controller

        :param window: Window instance
        """
        self.window = window
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
            "temperature": {
                "type": "float",
                "slider": True,
                "label": "preset.temperature",
                "min": 0,
                "max": 2,
                "step": 1,
                "multiplier": 100,
            },
            "model": {
                "label": "toolbox.model.label",
                "type": "combo",
                "use": "models",
                "keys": [],
            },
            "prompt": {
                "type": "textarea",
                "label": "preset.prompt",
            },
        }
        self.id = "preset"

    def get_options(self):
        """
        Get preset options

        :return: preset options
        """
        return self.options

    def get_option(self, id: str):
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

    def hook_update(self, key, value, caller, *args, **kwargs):
        """
        Hook: on settings update
        """
        mode = self.window.core.config.get('mode')
        if key == "prompt":
            self.window.core.config.set('prompt', value)
            if mode == 'assistant':
                self.window.controller.assistant.from_global()
                self.window.controller.presets.from_global()
            else:
                self.window.controller.presets.from_global()

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
        self.window.ui.dialogs.open_editor('editor.preset.presets', idx)

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

        # set focus to name field
        self.window.ui.config[self.id]['name'].setFocus()

    def save(self, force: bool = False):
        """
        Save ore create preset

        :param force: force overwrite file
        """
        id = self.window.controller.config.get_value(
            self.id,
            "filename",
            self.options["filename"],
        )
        mode = self.window.core.config.get("mode")

        # disallow editing current preset cache
        if id.startswith("current."):
            return

        if id is None or id == "":
            name = self.window.controller.config.get_value(
                self.id,
                "name",
                self.options["name"],
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
            self.window.core.presets.items[id] = PresetItem()
        elif not force:
            self.window.ui.dialogs.confirm(
                'preset_exists',
                id,
                trans('confirm.preset.overwrite'),
            )
            return

        # check if at least one mode is selected
        modes = ["chat", "completion", "img", "vision", "langchain", "assistant", "agent", "llama_index"]
        is_mode = False
        for mode in modes:
            if self.window.controller.config.get_value(
                    self.id,
                    mode,
                    self.options[mode],
            ):
                is_mode = True
                break
        if not is_mode:
            self.window.ui.dialogs.alert(
                trans('alert.preset.no_chat_completion')
            )
            return

        # assign data from fields to preset object in items
        self.assign_data(id)

        # apply changes to current active preset
        current = self.window.core.config.get('preset')
        if current is not None and current == id:
            self.to_current(self.window.core.presets.items[id])
            self.window.core.config.save()

        # save
        self.window.core.presets.save(id)
        self.window.controller.presets.refresh()

        # close dialog
        self.window.ui.dialogs.close('editor.preset.presets')
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
            data_dict[key] = self.window.controller.config.get_value(
                self.id,
                key,
                self.options[key],
            )
        if data_dict['name'] is None or data_dict['name'] == "":
            data_dict['name'] = id + " " + trans('preset.untitled')
        if data_dict['model'] == '_':
            data_dict['model'] = None
        self.window.core.presets.items[id].from_dict(data_dict)

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
            self.id,
            "ai_name",
            self.options["ai_name"],
            self.window.core.config.get('ai_name'),
        )
        self.window.controller.config.apply_value(
            self.id,
            "user_name",
            self.options["user_name"],
            self.window.core.config.get('user_name'),
        )
        self.window.controller.config.apply_value(
            self.id,
            "prompt",
            self.options["prompt"],
            self.window.core.config.get('prompt'),
        )
        self.window.controller.config.apply_value(
            self.id,
            "temperature",
            self.options["temperature"],
            self.window.core.config.get('temperature'),
        )
        self.window.controller.config.apply_value(
            self.id,
            "model",
            self.options["model"],
            self.window.core.config.get('model'),
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
