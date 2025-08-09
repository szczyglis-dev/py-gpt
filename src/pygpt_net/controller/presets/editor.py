#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.09 19:00:00                  #
# ================================================== #

import datetime
import os
import shutil
from typing import Any, Optional, Dict

from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_IMAGE,
    MODE_RESEARCH,
    MODE_COMPUTER,
)
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
        self.built = False
        self.tab_options_idx = {}
        self.opened = False
        self.tmp_avatar = None
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
            "ai_avatar": {
                "type": "text",
                "label": "preset.ai_avatar",
            },
            "ai_personalize": {
                "type": "bool",
                "label": "preset.ai_personalize",
                "description": "preset.ai_personalize.desc",
            },
            "user_name": {
                "type": "text",
                "label": "preset.user_name",
            },
            "description": {
                "type": "textarea",
                "label": "preset.description",
                "placeholder": "preset.description.desc",
            },
            MODE_IMAGE: {
                "type": "bool",
                "label": "preset.img",
            },
            MODE_CHAT: {
                "type": "bool",
                "label": "preset.chat",
            },
            MODE_COMPLETION: {
                "type": "bool",
                "label": "preset.completion",
            },
            MODE_VISION: {
                "type": "bool",
                "label": "preset.vision",
            },
            #MODE_LANGCHAIN: {
            #    "type": "bool",
            #    "label": "preset.langchain",
            #},
            MODE_EXPERT: {
                "type": "bool",
                "label": "preset.expert",
            },
            MODE_AGENT_LLAMA: {
                "type": "bool",
                "label": "preset.agent_llama",
            },
            MODE_AGENT: {
                "type": "bool",
                "label": "preset.agent",
            },
            MODE_AGENT_OPENAI: {
                "type": "bool",
                "label": "preset.agent_openai",
            },
            MODE_AUDIO: {
                "type": "bool",
                "label": "preset.audio",
            },
            MODE_RESEARCH: {
                "type": "bool",
                "label": "preset.research",
            },
            # "assistant": {
            # "type": "bool",
            # "label": "preset.assistant",
            # },
            MODE_LLAMA_INDEX: {
                "type": "bool",
                "label": "preset.llama_index",
            },
            MODE_COMPUTER: {
                "type": "bool",
                "label": "preset.computer",
            },
            "model": {
                "label": "toolbox.model.label",
                "type": "combo",
                "use": "models",
            },
            "remote_tools": {
                "label": "toolbox.remote_tools.label",
                "type": "bool_list",
                "use": "remote_tools_openai",
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
                "label": "",
                "context_options": ["prompt.template.paste"],
            },
            "idx": {
                "type": "combo",
                "label": "preset.idx",
                "description": "preset.idx.desc",
                "use": "idx",
            },
            "agent_provider": {
                "type": "combo",
                "label": "preset.agent_provider",
                "description": "preset.agent_provider.desc",
                "use": "agent_provider_llama",
            },
            "agent_provider_openai": {
                "type": "combo",
                "label": "preset.agent_provider",
                "description": "preset.agent_provider.desc",
                "use": "agent_provider_openai",
            },
            "assistant_id": {
                "type": "text",
                "label": "preset.assistant_id",
                "description": "preset.assistant_id.desc",
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
        self.hidden_by_mode = {  # hidden fields by mode
            MODE_CHAT: ["idx"],
            MODE_AGENT_LLAMA: ["temperature"],
            MODE_AGENT_OPENAI: ["temperature"],
        }
        self.id = "preset"
        self.current = None

    def get_options(self) -> Dict[str, Dict[str, Any]]:
        """
        Get preset options

        :return: preset options
        """
        return self.options

    def get_option(self, id: str) -> Dict[str, Any]:
        """
        Get preset option

        :param id: option id
        :return: preset option
        """
        return self.options[id]

    def show_hide_by_mode(self):
        """Show or hide fields by mode"""
        # TODO: implement this!
        return
        mode = self.window.core.config.get('mode')
        for key in self.options:
            if mode in self.hidden_by_mode:
                if key in self.hidden_by_mode[mode]:
                    self.window.ui.config[self.id][key].setVisible(False)
                    label = 'preset.' + key + '.label'
                    if label in self.window.ui.nodes:
                        self.window.ui.nodes[label].setVisible(False)
                else:
                    self.window.ui.config[self.id][key].setVisible(True)
                    label = 'preset.' + key + '.label'
                    if label in self.window.ui.nodes:
                        self.window.ui.nodes[label].setVisible(True)

    def setup(self):
        """Setup preset editor"""
        # update after agents register
        self.append_extra_config()
        self.window.ui.config[self.id]['agent_provider'].set_keys(
            self.window.controller.config.placeholder.apply_by_id('agent_provider_llama')
        )
        self.window.ui.config[self.id]['agent_provider_openai'].set_keys(
            self.window.controller.config.placeholder.apply_by_id('agent_provider_openai')
        )

        # add hooks for config update in real-time
        self.window.ui.add_hook("update.preset.prompt", self.hook_update)
        self.window.ui.add_hook("update.preset.agent_provider_openai", self.hook_update)

        # register functions dictionary
        parent = "preset"
        key = "tool.function"
        self.window.ui.dialogs.register_dictionary(
            key,
            parent,
            self.get_option(key),
        )

    def toggle_extra_options(self):
        """
        Toggle extra options in preset editor

        :return: None
        """
        if not self.tab_options_idx:
            return
        mode = self.window.core.config.get('mode')
        if mode != MODE_AGENT_OPENAI:
            # show base prompt
            self.window.ui.tabs['preset.editor.extra'].setTabVisible(0, True)
            # hide all tabs
            for id in self.tab_options_idx:
                for tab_idx in self.tab_options_idx[id]:
                    if self.window.ui.tabs['preset.editor.extra'].count() >= tab_idx:
                        self.window.ui.tabs['preset.editor.extra'].setTabVisible(tab_idx, False)
            return
        else:
            # hide all tabs
            for id in self.tab_options_idx:
                for tab_idx in self.tab_options_idx[id]:
                    if self.window.ui.tabs['preset.editor.extra'].count() >= tab_idx:
                        self.window.ui.tabs['preset.editor.extra'].setTabVisible(tab_idx, False)

            self.toggle_extra_options_by_provider()

    def toggle_extra_options_by_provider(self):
        """
        Toggle extra options in preset editor by provider

        :return: None
        """
        if not self.tab_options_idx:
            # show base prompt
            self.window.ui.tabs['preset.editor.extra'].setTabVisible(0, True)
            return
        mode = self.window.core.config.get('mode')
        if mode == MODE_AGENT_OPENAI:
            current_provider = self.window.controller.config.get_value(
                parent_id=self.id,
                key="agent_provider_openai",
                option=self.options["agent_provider_openai"],
            )
            if current_provider is None or current_provider == "":
                # show base prompt
                self.window.ui.tabs['preset.editor.extra'].setTabVisible(0, True)
                return

            # show all tabs for current provider
            for id in self.tab_options_idx:

                self.window.ui.tabs['preset.editor.extra'].setTabVisible(0, False)

                if id != current_provider:
                    for tab_idx in self.tab_options_idx[id]:
                        if self.window.ui.tabs['preset.editor.extra'].count() >= tab_idx:
                            self.window.ui.tabs['preset.editor.extra'].setTabVisible(tab_idx, False)
                else:
                    for tab_idx in self.tab_options_idx[id]:
                        if self.window.ui.tabs['preset.editor.extra'].count() >= tab_idx:
                            self.window.ui.tabs['preset.editor.extra'].setTabVisible(tab_idx, True)

            # show base prompt if no custom options in current agent
            agent = self.window.core.agents.provider.get(current_provider)
            if not agent:
                self.window.ui.tabs['preset.editor.extra'].setTabVisible(0, True)
                return
            option_tabs = agent.get_options()
            if not option_tabs or len(option_tabs) == 0:
                self.window.ui.tabs['preset.editor.extra'].setTabVisible(0, True)

    def load_extra_options(self, preset: PresetItem):
        """
        Load extra options for preset editor

        :param preset: preset item
        """
        if preset.agent_provider_openai is None or preset.agent_provider_openai == "":
            return

        # update options in UI
        id = preset.agent_provider_openai
        agent = self.window.core.agents.provider.get(id)
        if not agent:
            return
        if not preset.extra or id not in preset.extra:
            return
        data_dict = preset.extra[id]
        option_tabs = agent.get_options()
        for option_tab_id in data_dict:
            option_key = "agent." + preset.agent_provider_openai + "." + option_tab_id
            if option_key not in self.window.ui.config:
                continue
            extra_options = option_tabs.get(option_tab_id, {}).get('options', {})
            for key in extra_options:
                value = data_dict[option_tab_id].get(key, None)
                if value is not None:
                    self.window.controller.config.apply_value(
                        parent_id=option_key,
                        key=key,
                        option=extra_options[key],
                        value=value,
                    )
                else:
                    # from defaults
                    if "default" not in extra_options[key]:
                        continue
                    self.window.controller.config.apply_value(
                        parent_id=option_key,
                        key=key,
                        option=extra_options[key],
                        value=extra_options[key].get('default', None),
                    )

    def load_extra_defaults(self):
        """
        Load extra options defaults for preset editor

        :return: None
        """
        if not self.tab_options_idx:
            return
        mode = self.window.core.config.get('mode')
        if mode != MODE_AGENT_OPENAI:
            return

        # load defaults for all tabs
        for id in self.tab_options_idx:
            agent = self.window.core.agents.provider.get(id)
            if not agent:
                continue
            option_tabs = agent.get_options()
            for option_tab_id in option_tabs:
                option_key = "agent." + id + "." + option_tab_id
                if option_key not in self.window.ui.config:
                    continue
                extra_options = option_tabs[option_tab_id]['options']
                for key in extra_options:
                    value = extra_options[key].get('default', None)
                    if value is not None:
                        self.window.controller.config.apply_value(
                            parent_id=option_key,
                            key=key,
                            option=extra_options[key],
                            value=value,
                        )

    def load_extra_defaults_current(self):
        """
        Load extra options defaults on mode change

        :return: None
        """
        if not self.tab_options_idx:
            return

        if not self.current:
            return

        mode = self.window.core.config.get('mode')
        if mode != MODE_AGENT_OPENAI:
            return

        preset = self.window.core.presets.get_by_uuid(self.current)
        if not preset:
            return
        current_provider_id = preset.agent_provider_openai if preset else None

        # load defaults for all tabs
        for id in self.tab_options_idx:
            # skip current provider
            if current_provider_id and id == current_provider_id:
                continue
            agent = self.window.core.agents.provider.get(id)
            if not agent:
                continue
            option_tabs = agent.get_options()
            for option_tab_id in option_tabs:
                option_key = "agent." + id + "." + option_tab_id
                if option_key not in self.window.ui.config:
                    continue
                extra_options = option_tabs[option_tab_id]['options']
                for key in extra_options:
                    value = extra_options[key].get('default', None)
                    if value is not None:
                        # check current, apply only if current is empty
                        current_value = self.window.controller.config.get_value(
                            parent_id=option_key,
                            key=key,
                            option=extra_options[key],
                        )
                        if current_value is not None and current_value != "":
                            continue

                        self.window.controller.config.apply_value(
                            parent_id=option_key,
                            key=key,
                            option=extra_options[key],
                            value=value,
                        )

    def append_extra_options(self, preset: PresetItem):
        """
        Get extra options for preset editor

        :param id: preset id
        :param preset: preset item
        """
        exclude_ids = [
            "__prompt__",
        ]
        id = preset.agent_provider_openai
        options = {}
        agent = self.window.core.agents.provider.get(id)
        if not agent:
            return options
        option_tabs = agent.get_options()
        if not option_tabs:
            return options
        data_dict = {}
        for option_tab_id in option_tabs:
            if option_tab_id in exclude_ids:
                continue
            option_key = "agent." + id + "." + option_tab_id
            if option_key not in self.window.ui.config:
                continue
            if option_tab_id not in data_dict:
                data_dict[option_tab_id] = {}
            extra_options = option_tabs[option_tab_id]['options']
            for key in extra_options:
                data_dict[option_tab_id][key] = self.window.controller.config.get_value(
                    parent_id=option_key,
                    key=key,
                    option=extra_options[key],
                )
        if preset.extra is None:
            preset.extra = {}
        preset.extra[id] = data_dict

    def append_extra_config(self):
        """
        Build extra configuration for the preset editor dialog
        """
        if self.built:
            return

        exclude_ids = [
            "__prompt__",
        ]
        agents = self.window.core.agents.provider.all()
        tabs = self.window.ui.tabs['preset.editor.extra']
        tab_idx = 1
        for id in agents:
            agent = agents[id]
            option_tabs = agent.get_options()
            if not option_tabs:
                continue

            # append tabs
            for option_tab_id in option_tabs:
                if option_tab_id in exclude_ids:
                    continue

                option = option_tabs[option_tab_id]
                title = option.get('label', '')
                config_id = "agent." + id + "." + option_tab_id
                widgets, options = self.window.ui.dialogs.preset.build_option_widgets(config_id, option['options'])
                layout = QVBoxLayout()
                layout.setContentsMargins(0, 10, 0, 10)

                checkboxLayout = QHBoxLayout()
                for key in options:
                    opt_layout = options[key]
                    if option['options'][key]['type'] == 'bool':
                        # checkbox
                        checkboxLayout.addLayout(opt_layout)
                    else:
                        layout.addLayout(opt_layout)
                layout.addLayout(checkboxLayout)

                # as tab
                tab_widget = QWidget()
                tab_widget.setLayout(layout)
                tabs.addTab(tab_widget, title)

                # store mapping: agent id -> [tab index]
                if id not in self.tab_options_idx:
                    self.tab_options_idx[id] = []
                if tab_idx not in self.tab_options_idx[id]:
                    self.tab_options_idx[id].append(tab_idx)
                tab_idx += 1

        self.built = True

    def append_default_prompt(self):
        """
        Append default prompt to the preset editor

        :return: None
        """
        mode = self.window.core.config.get('mode')
        if mode != MODE_AGENT_OPENAI:
            return

        # get current provider
        current_provider = self.window.controller.config.get_value(
            parent_id=self.id,
            key="agent_provider_openai",
            option=self.options["agent_provider_openai"],
        )
        if current_provider is None or current_provider == "":
            return

        # get agent by provider
        agent = self.window.core.agents.provider.get(current_provider)
        if not agent:
            return

        # get default prompt
        default_prompt = agent.get_default_prompt()
        if default_prompt is None or default_prompt == "":
            return

        # set default prompt to the prompt field
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="prompt",
            option=self.options["prompt"],
            value=default_prompt,
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
        Hook: on settings update in real-time (prompt)

        :param key: setting key
        :param value: setting value
        :param caller: caller id
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        mode = self.window.core.config.get('mode')
        if key == "prompt":
            self.window.core.config.set('prompt', value)
            if mode == MODE_ASSISTANT:
                self.window.controller.assistant.from_global()  # update current assistant, never called!!!!!
            else:
                self.window.controller.presets.from_global()  # update current preset

        # show/hide extra options
        elif key == "agent_provider_openai":
            self.toggle_extra_options_by_provider()
            self.append_default_prompt()
            self.load_extra_defaults_current()

    def edit(self, idx: Optional[int] = None):
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

    def init(self, id: Optional[str] = None):
        """
        Initialize preset editor

        :param id: preset id (filename)
        """
        self.opened = True
        data = PresetItem()
        data.name = ""
        data.filename = ""

        if id is None:
            self.experts.update_list()

        if id is not None and id != "":
            if id in self.window.core.presets.items:
                data = self.window.core.presets.items[id]
                data.filename = id
                self.current = data.uuid
        else:
            self.load_extra_defaults()

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
            if mode == MODE_CHAT:
                data.chat = True
            elif mode == MODE_COMPLETION:
                data.completion = True
            elif mode == MODE_IMAGE:
                data.img = True
            elif mode == MODE_VISION:
                data.vision = True
            # elif mode == MODE_LANGCHAIN:
                # data.langchain = True
            # elif mode == MODE_ASSISTANT:
                # data.assistant = True
            elif mode == MODE_LLAMA_INDEX:
                data.llama_index = True
            elif mode == MODE_EXPERT:
                data.expert = True
            elif mode == MODE_AGENT:
                data.agent = True
            elif mode == MODE_AGENT_LLAMA:
                data.agent_llama = True
            elif mode == MODE_AGENT_OPENAI:
                data.agent_openai = True
            elif mode == MODE_AUDIO:
                data.audio = True
            elif mode == MODE_RESEARCH:
                data.research = True
            elif mode == MODE_COMPUTER:
                data.computer = True

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

        # load extra options
        self.load_extra_options(data)

        self.toggle_extra_options()

        # update experts list, after ID loaded
        self.experts.update_list()

        # setup avatar config
        self.update_avatar_config(data)

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
        current_model = self.window.core.config.get('model')
        # set current model in combo box as selected
        if id is None:
            self.window.ui.config[self.id]['model'].set_value(current_model)
        self.window.ui.config[self.id]['name'].setFocus()
        self.show_hide_by_mode()
        self.toggle_extra_options_by_provider()
        if id is None:
            self.append_default_prompt()

    def save(
            self,
            force: bool = False,
            close: bool = True
    ):
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
        modes = [
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_IMAGE,
            MODE_VISION,
            # MODE_LANGCHAIN,
            MODE_LLAMA_INDEX,
            MODE_EXPERT,
            MODE_AGENT_LLAMA,
            MODE_AGENT,
            MODE_AGENT_OPENAI,
            MODE_AUDIO,
            MODE_COMPUTER,
        ]

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
                self.window.update_status(trans('status.preset.empty_id'))
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
        is_new = False
        if id not in self.window.core.presets.items:
            is_new = True
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
        if mode != MODE_AGENT and not is_mode:
            self.window.ui.dialogs.alert(
                trans('alert.preset.no_chat_completion')
            )
            return

        # assign data from fields to preset object in items
        self.assign_data(id)

        if is_new:
            # assign tmp avatar
            if self.tmp_avatar is not None:
                self.window.core.presets.items[id].ai_avatar = self.tmp_avatar
                self.tmp_avatar = None
        else:
            self.tmp_avatar = None

        # if agent, assign experts and select only agent mode
        curr_mode = self.window.core.config.get('mode')
        if curr_mode == MODE_AGENT:
            self.window.core.presets.items[id].mode = [MODE_AGENT]
        elif curr_mode == MODE_AGENT_LLAMA:
            self.window.core.presets.items[id].mode = [MODE_AGENT_LLAMA]
        elif curr_mode == MODE_AGENT_OPENAI:
            self.window.core.presets.items[id].mode = [MODE_AGENT_OPENAI]

        # apply changes to current active preset
        current = self.window.core.config.get('preset')
        if current is not None and current == id:
            self.to_current(self.window.core.presets.items[id])
            self.window.core.config.save()

        # update current uuid
        self.current = self.window.core.presets.items[id].uuid

        # save
        no_scroll = False
        if not is_new:
            no_scroll = True
        self.window.core.presets.save(id)
        self.window.controller.presets.refresh(no_scroll=no_scroll)

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
        self.window.update_status(trans('status.preset.saved'))

        # sort by name
        self.window.core.presets.sort_by_name()

        # switch to editing preset, if new
        if is_new:
            self.window.controller.presets.set(mode, id)
            self.window.controller.presets.select_model()
        else:
            # switch to model if current preset
            current_preset = self.window.core.config.get('preset')
            if current_preset is not None and current_preset == id:
                self.window.controller.presets.set(mode, current_preset)
                self.window.controller.presets.select_model()

        # update presets list
        no_scroll = False
        if not is_new:
            no_scroll = True
        self.window.controller.presets.refresh(no_scroll=no_scroll)
        self.opened = False

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
        preset.filename = id
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

        # extra options
        self.append_extra_options(preset)

        # avatar update
        self.update_avatar_config(preset)

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

    def update_from_global(self, key: str, value: Any):
        """
        Update field from global config

        :param key: field key
        :param value: field value
        """
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

    def upload_avatar(self, file_path: str):
        """
        Update avatar config for preset

        :param file_path: path to the avatar file
        """
        preset = self.window.core.presets.get_by_uuid(self.current)
        presets_dir = self.window.core.config.get_user_dir("presets")
        avatars_dir = os.path.join(presets_dir, "avatars")
        preset_name = "_" if preset is None else preset.filename
        if not os.path.exists(avatars_dir):
            os.makedirs(avatars_dir, exist_ok=True)
        file_ext = os.path.splitext(file_path)[1]
        store_name = preset_name + "_" + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + file_ext
        avatar_path = os.path.join(avatars_dir, store_name)

        # copy avatar to avatars directory
        if os.path.exists(avatar_path):
            os.remove(avatar_path)
        if os.path.exists(file_path):
            shutil.copy(file_path, avatar_path)
            if preset:
                preset.ai_avatar = store_name
            else:
                self.tmp_avatar = store_name
            self.window.controller.config.apply_value(
                parent_id=self.id,
                key="ai_avatar",
                option=self.options["ai_avatar"],
                value=store_name,
            )
            self.window.ui.nodes['preset.editor.avatar'].load_avatar(avatar_path)
            self.window.ui.nodes['preset.editor.avatar'].enable_remove_button(True)
        return avatar_path

    def update_avatar_config(self, preset: PresetItem):
        """
        Update avatar config for preset

        :param preset: preset item
        """
        avatar_path = preset.ai_avatar
        if avatar_path:
            file_path = os.path.join(
                self.window.core.config.get_user_dir("presets"),
                "avatars",
                avatar_path,
            )
            if not os.path.exists(file_path):
                self.window.ui.nodes['preset.editor.avatar'].remove_avatar()
                print("Avatar file does not exist:", file_path)
                return
            self.window.ui.nodes['preset.editor.avatar'].load_avatar(file_path)
            self.window.ui.nodes['preset.editor.avatar'].enable_remove_button(True)
        else:
            self.window.ui.nodes['preset.editor.avatar'].remove_avatar()

    def remove_avatar(self, force: bool = False):
        """
        Remove avatar from preset editor

        :param force: force remove avatar
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='preset.avatar.delete',
                id="",
                msg=trans('confirm.preset.avatar.delete'),
            )
            return
        preset = self.window.core.presets.get_by_uuid(self.current)
        if preset:
            current = preset.ai_avatar
            if current:
                presets_dir = self.window.core.config.get_user_dir("presets")
                avatars_dir = os.path.join(presets_dir, "avatars")
                avatar_path = os.path.join(avatars_dir, current)
                if os.path.exists(avatar_path):
                    os.remove(avatar_path)
            preset.ai_avatar = ""
        else:
            self.tmp_avatar = None

        self.window.ui.nodes['preset.editor.avatar'].remove_avatar()
        self.window.controller.config.apply_value(
            parent_id=self.id,
            key="ai_avatar",
            option=self.options["ai_avatar"],
            value="",
        )
