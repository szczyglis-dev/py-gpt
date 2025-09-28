#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.28 08:00:00                  #
# ================================================== #

import datetime
import os
import shutil
from typing import Any, Optional, Dict

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QScrollArea, QFrame

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

    TAB_IDX = {
        "general": 0,
        "personalize": 1,
        "experts": 2,
        "remote_tools": 3,
    }

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
                "type": "text",
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
            #MODE_VISION: {
            #   "type": "bool",
            #    "label": "preset.vision",
            #},
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
                "extra": {
                    "urls": {
                        "Help": "https://pygpt.readthedocs.io/en/latest/modes.html#agent-llamaindex"
                    },
                }
            },
            "agent_provider_openai": {
                "type": "combo",
                "label": "preset.agent_provider",
                "description": "preset.agent_provider.desc",
                "use": "agent_provider_openai",
                "extra": {
                    "urls": {
                        "Help": "https://pygpt.readthedocs.io/en/latest/modes.html#agent-openai"
                    },
                }
            },
        }
        self.hidden_by_mode = {  # hidden fields by mode
            MODE_CHAT: ["idx"],
            MODE_AGENT_LLAMA: ["temperature"],
            MODE_AGENT_OPENAI: ["temperature"],
        }
        self.id = "preset"
        self.current = None
        self.current_id = None

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
        self.update_providers_list()

        # add hooks for config update in real-time
        self.window.ui.add_hook("update.preset.prompt", self.hook_update)
        self.window.ui.add_hook("update.preset.agent_provider", self.hook_update)
        self.window.ui.add_hook("update.preset.agent_provider_openai", self.hook_update)

    def toggle_extra_options(self):
        """Toggle extra options in preset editor"""
        if not self.tab_options_idx:
            return
        mode = self.window.core.config.get('mode')
        tabs = self.window.ui.tabs['preset.editor.extra']
        if mode not in [MODE_AGENT_OPENAI, MODE_AGENT_LLAMA]:
            tabs.setTabVisible(0, True)  # show base prompt
            for opt_id in self.tab_options_idx:  # hide all tabs
                for tab_idx in self.tab_options_idx[opt_id]:
                    if tabs.count() > tab_idx:
                        tabs.setTabVisible(tab_idx, False)
            return
        else:
            for opt_id in self.tab_options_idx:  # hide all tabs
                for tab_idx in self.tab_options_idx[opt_id]:
                    if tabs.count() > tab_idx:
                        tabs.setTabVisible(tab_idx, False)

            self.toggle_extra_options_by_provider()

    def toggle_extra_options_by_provider(self):
        """Toggle extra options in preset editor by provider"""
        tabs = self.window.ui.tabs['preset.editor.extra']

        if not self.tab_options_idx:
            tabs.setTabVisible(0, True)  # base prompt
            return

        mode = self.window.core.config.get('mode')
        key_agent = ""

        if mode in [MODE_AGENT_OPENAI, MODE_AGENT_LLAMA]:
            key_agent = "agent_provider_openai" if mode == MODE_AGENT_OPENAI else "agent_provider"

            # 1) try from UI
            current_provider = self.window.controller.config.get_value(
                parent_id=self.id,
                key=key_agent,
                option=self.options[key_agent],
            )

            # 2) fallback to current preset
            if not current_provider or current_provider == "_":
                preset = self.window.core.presets.get_by_uuid(self.current)
                if preset:
                    current_provider = getattr(preset, key_agent, None)

            # 3) if still not set -> show base prompt
            if not current_provider or current_provider == "_":
                tabs.setTabVisible(0, True)
                return

            # first hide all tabs
            for opt_id in self.tab_options_idx:
                for tab_idx in self.tab_options_idx[opt_id]:
                    if tabs.count() > tab_idx:
                        tabs.setTabVisible(tab_idx, False)

            # hide base prompt
            tabs.setTabVisible(0, False)

            # show tabs for current provider
            for tab_idx in self.tab_options_idx.get(current_provider, []):
                if tabs.count() > tab_idx:
                    tabs.setTabVisible(tab_idx, True)

            # if not found, show base prompt
            agent = self.window.core.agents.provider.get(current_provider, mode)
            if not agent:
                tabs.setTabVisible(0, True)
                return
            option_tabs = agent.get_options()
            if not option_tabs:
                tabs.setTabVisible(0, True)
        else:
            # not agent mode -> show base prompt
            tabs.setTabVisible(0, True)

    def load_extra_options(self, preset: PresetItem):
        """
        Load extra options for preset editor

        :param preset: preset item
        """
        mode = self.window.core.config.get('mode')
        if mode == MODE_AGENT_OPENAI:
            if preset.agent_provider_openai is None or preset.agent_provider_openai == "":
                return
            id = preset.agent_provider_openai
        elif mode == MODE_AGENT_LLAMA:
            if preset.agent_provider is None or preset.agent_provider == "":
                return
            id = preset.agent_provider
        else:
            return

        # update options in UI
        agent = self.window.core.agents.provider.get(id, mode)
        if not agent:
            return
        if not preset.extra or id not in preset.extra:
            return

        apply_value = self.window.controller.config.apply_value

        data_dict = preset.extra[id]
        option_tabs = agent.get_options()
        for option_tab_id in data_dict:
            parent_key = ""
            if mode == MODE_AGENT_OPENAI:
                parent_key = preset.agent_provider_openai
            elif mode == MODE_AGENT_LLAMA:
                parent_key = preset.agent_provider
            option_key = "agent." + parent_key + "." + option_tab_id
            if option_key not in self.window.ui.config:
                continue

            extra_options = option_tabs.get(option_tab_id, {}).get('options', {})
            for key in extra_options:
                value = data_dict[option_tab_id].get(key, None)
                if value is not None:
                    apply_value(
                        parent_id=option_key,
                        key=key,
                        option=extra_options[key],
                        value=value,
                    )
                else:
                    # from defaults
                    if "default" not in extra_options[key]:
                        continue
                    apply_value(
                        parent_id=option_key,
                        key=key,
                        option=extra_options[key],
                        value=extra_options[key].get('default', None),
                    )

            # ensure combo defaults are effectively applied for this tab (only empty values are updated)
            self._apply_combo_defaults_for_group(option_key, extra_options)

    def load_extra_defaults(self):
        """Load extra options defaults for preset editor"""
        if not self.tab_options_idx:
            return
        mode = self.window.core.config.get('mode')
        if mode not in [MODE_AGENT_OPENAI, MODE_AGENT_LLAMA]:
            return

        apply_value = self.window.controller.config.apply_value

        # load defaults for all tabs
        for id in self.tab_options_idx:
            agent = self.window.core.agents.provider.get(id, mode)
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
                        apply_value(
                            parent_id=option_key,
                            key=key,
                            option=extra_options[key],
                            value=value,
                        )
                # ensure combo defaults are effectively applied for this tab (only empty values are updated)
                self._apply_combo_defaults_for_group(option_key, extra_options)

    def load_extra_defaults_current(self):
        """Load extra options defaults on mode change"""
        if not self.tab_options_idx:
            return

        if not self.current:
            return

        mode = self.window.core.config.get('mode')
        if mode not in [MODE_AGENT_OPENAI, MODE_AGENT_LLAMA]:
            return

        preset = self.window.core.presets.get_by_uuid(self.current)
        if not preset:
            return

        current_provider_id = None
        if mode == MODE_AGENT_OPENAI:
            current_provider_id = preset.agent_provider_openai if preset else None
        elif mode == MODE_AGENT_LLAMA:
            current_provider_id = preset.agent_provider if preset else None

        get_value = self.window.controller.config.get_value
        apply_value = self.window.controller.config.apply_value

        # load defaults for all tabs
        for id in self.tab_options_idx:
            if current_provider_id and id == current_provider_id:
                continue  # skip current provider
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
                    if value is not None:  # check current, apply only if current is empty
                        current_value = get_value(
                            parent_id=option_key,
                            key=key,
                            option=extra_options[key],
                        )
                        if current_value is not None and current_value != "":
                            continue

                        apply_value(
                            parent_id=option_key,
                            key=key,
                            option=extra_options[key],
                            value=value,
                        )
                # ensure combo defaults are effectively applied for this tab (only empty values are updated)
                self._apply_combo_defaults_for_group(option_key, extra_options)

    def append_extra_options(self, preset: PresetItem):
        """
        Append extra options for preset editor

        :param preset: preset item
        """
        mode = self.window.core.config.get('mode')
        exclude_ids = [
            "__prompt__",
        ]
        if mode == MODE_AGENT_OPENAI:
            id = preset.agent_provider_openai
        elif mode == MODE_AGENT_LLAMA:
            id = preset.agent_provider
        else:
            return

        get_value = self.window.controller.config.get_value
        options = {}
        agent = self.window.core.agents.provider.get(id, mode)
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
                data_dict[option_tab_id][key] = get_value(
                    parent_id=option_key,
                    key=key,
                    option=extra_options[key],
                )
        if preset.extra is None:
            preset.extra = {}
        preset.extra[id] = data_dict

    def append_extra_config(self):
        """Build extra configuration for the preset editor dialog"""
        if self.built:
            return

        exclude_ids = [
            "__prompt__",
        ]
        agents = self.window.core.agents.provider.all()
        tabs = self.window.ui.tabs['preset.editor.extra']
        build_option_widgets = self.window.ui.dialogs.preset.build_option_widgets

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
                widgets, options = build_option_widgets(config_id, option['options'])
                layout = QVBoxLayout()
                layout.setContentsMargins(0, 10, 0, 10)

                checkbox_layout = QHBoxLayout()
                for key in options:
                    opt_layout = options[key]
                    if option['options'][key]['type'] == 'bool':
                        checkbox_layout.addLayout(opt_layout)   # checkbox
                    else:
                        layout.addLayout(opt_layout)
                layout.addStretch(1)
                layout.addLayout(checkbox_layout)

                # wrap the tab content in a scroll area to avoid vertical overlaps
                tab_content = QWidget()
                tab_content.setLayout(layout)

                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setWidget(tab_content)
                # Attach metadata on the tab widget itself for later mapping.
                scroll.setProperty("agent_id", id)
                scroll.setProperty("option_tab_id", option_tab_id)

                tabs.addTab(scroll, title)

                # store mapping: agent id -> [tab index]
                if id not in self.tab_options_idx:
                    self.tab_options_idx[id] = []
                if tab_idx not in self.tab_options_idx[id]:
                    self.tab_options_idx[id].append(tab_idx)
                tab_idx += 1

        self.built = True

    def _ensure_agent_tab_properties(self):
        """
        Ensure every existing extra tab has the 'agent_id' property set,
        based on current self.tab_options_idx mapping.
        This makes it possible to rebuild the mapping after insertions/removals.
        """
        tabs = self.window.ui.tabs['preset.editor.extra']
        if not tabs:
            return
        for a_id, indices in self.tab_options_idx.items():
            for idx in indices:
                if 0 < idx < tabs.count():
                    w = tabs.widget(idx)
                    if w is not None and not w.property("agent_id"):
                        w.setProperty("agent_id", a_id)

    def _rebuild_tab_index_mapping(self):
        """
        Rebuild self.tab_options_idx by scanning actual tabs and grouping by 'agent_id' property.
        Base prompt tab (index 0) is ignored.
        """
        tabs = self.window.ui.tabs['preset.editor.extra']
        new_map = {}
        if not tabs:
            self.tab_options_idx = new_map
            return

        for i in range(1, tabs.count()):
            w = tabs.widget(i)
            if w is None:
                continue
            a_id = w.property("agent_id")
            if not a_id:
                # If a tab has no agent tag, we skip it; it's not an "agent extra" tab.
                continue
            if a_id not in new_map:
                new_map[a_id] = []
            new_map[a_id].append(i)

        self.tab_options_idx = new_map

    def update_custom_agent_options(self, agent_id: str):
        """
        Rebuild extra option tabs for a given agent_id at runtime, keeping indices consistent.

        What it does:
        - Removes all existing tabs for this agent (and their UI config groups).
        - If agent exists, creates fresh tabs from agent.get_options().
          - Applies saved values from current preset.extra[agent_id] when available.
          - Otherwise applies defaults defined in option schema.
        - If agent does not exist, simply clears tabs and config for this agent.
        - Recomputes self.tab_options_idx so it always matches the current QTabWidget.
        - Finally, re-runs visibility logic so only relevant tabs are shown.

        Notes:
        - Base prompt tab is index 0 and remains untouched.
        - This method must be called in the UI thread (Qt).
        """
        tabs = self.window.ui.tabs['preset.editor.extra']
        if not tabs:
            return

        # Make sure existing tabs have proper metadata to allow safe remapping later.
        self._ensure_agent_tab_properties()

        mode = self.window.core.config.get('mode')
        exclude_ids = ["__prompt__"]

        # Old indices for this agent (if any), sorted to compute insertion position and to remove safely.
        old_indices = sorted(self.tab_options_idx.get(agent_id, []))
        # Prefer to keep the first old index as insertion anchor to preserve overall ordering.
        insertion_index = old_indices[0] if old_indices else tabs.count()

        # 1) Remove old tabs for this agent (descending order to avoid index shifts).
        for idx in sorted(old_indices, reverse=True):
            if 0 < idx < tabs.count():
                w = tabs.widget(idx)
                tabs.removeTab(idx)
                if w is not None:
                    w.deleteLater()

        # Remove old UI config groups for this agent (they will be rebuilt).
        # We assume self.window.ui.config is a dict-like structure holding per-parent groups.
        cfg = self.window.ui.config
        for key in list(cfg.keys()):
            if isinstance(key, str) and key.startswith(f"agent.{agent_id}."):
                try:
                    del cfg[key]
                except Exception:
                    pass

        # Clear mapping entry for this agent; we will rebuild mapping from scratch later.
        if agent_id in self.tab_options_idx:
            del self.tab_options_idx[agent_id]

        # 2) Fetch fresh options from provider.
        agent = self.window.core.agents.provider.get(agent_id, mode)
        if not agent:
            # Agent no longer exists -> just rebuild mapping for remaining tabs and update visibility.
            self._rebuild_tab_index_mapping()
            self.toggle_extra_options_by_provider()
            return

        option_tabs = agent.get_options() or {}

        # If agent has no custom option tabs -> nothing to add (base prompt will be used).
        # Still need to rebuild mapping and visibility.
        if len(option_tabs) == 0:
            self._rebuild_tab_index_mapping()
            self.toggle_extra_options_by_provider()
            return

        build_option_widgets = self.window.ui.dialogs.preset.build_option_widgets
        apply_value = self.window.controller.config.apply_value

        # Try to load saved values for current preset (if this agent is used in it).
        preset = self.window.core.presets.get_by_uuid(self.current)
        saved_data = None
        if preset and preset.extra and agent_id in preset.extra:
            # Expected structure: preset.extra[agent_id][option_tab_id][key] = value
            saved_data = preset.extra.get(agent_id, None)

        # Figure out if this agent is the currently selected provider for the active mode.
        # If yes, we will prefer saved values from preset.extra; otherwise we apply defaults.
        selected_provider_id = None
        if mode in [MODE_AGENT_OPENAI, MODE_AGENT_LLAMA]:
            key_agent = "agent_provider_openai" if mode == MODE_AGENT_OPENAI else "agent_provider"
            selected_provider_id = self.window.controller.config.get_value(
                parent_id=self.id,
                key=key_agent,
                option=self.options[key_agent],
            )

        # 3) Create new tabs from fresh schema and insert them at the computed anchor.
        new_indices = []
        for option_tab_id, option_desc in option_tabs.items():
            if option_tab_id in exclude_ids:
                continue

            title = option_desc.get('label', '')
            config_id = f"agent.{agent_id}.{option_tab_id}"
            schema_options = option_desc.get('options', {}) or {}

            # Build new option widgets into UI config under config_id.
            widgets, options_layouts = build_option_widgets(config_id, schema_options)

            # Create layouts similar to initial build (checkboxes at bottom row).
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 10, 0, 10)

            checkbox_layout = QHBoxLayout()
            for key, opt_layout in options_layouts.items():
                opt_schema = schema_options.get(key, {})
                if opt_schema.get('type') == 'bool':
                    checkbox_layout.addLayout(opt_layout)
                else:
                    layout.addLayout(opt_layout)
            layout.addStretch(1)
            layout.addLayout(checkbox_layout)

            # Assemble tab widget wrapped into a scroll area.
            tab_content = QWidget()
            tab_content.setLayout(layout)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(tab_content)
            scroll.setProperty('agent_id', agent_id)
            scroll.setProperty('option_tab_id', option_tab_id)

            # Insert at a stable anchor to preserve general ordering between agents.
            insertion_index = min(insertion_index, tabs.count())
            tabs.insertTab(insertion_index, scroll, title)
            new_indices.append(insertion_index)
            insertion_index += 1

            # Apply values:
            # - If this agent is currently selected for the active mode and we have saved_data,
            #   prefer saved values from preset.extra.
            # - Otherwise apply defaults from schema (when provided).
            group_cfg = self.window.ui.config.get(config_id, {})
            if selected_provider_id == agent_id and saved_data and option_tab_id in saved_data:
                data_dict = saved_data[option_tab_id] or {}
                for key, opt_schema in schema_options.items():
                    if key in data_dict:
                        apply_value(
                            parent_id=config_id,
                            key=key,
                            option=opt_schema,
                            value=data_dict[key],
                        )
                    elif 'default' in opt_schema:
                        apply_value(
                            parent_id=config_id,
                            key=key,
                            option=opt_schema,
                            value=opt_schema.get('default'),
                        )
            else:
                # Apply defaults only (do not overwrite elsewhere).
                for key, opt_schema in schema_options.items():
                    if 'default' in opt_schema:
                        apply_value(
                            parent_id=config_id,
                            key=key,
                            option=opt_schema,
                            value=opt_schema.get('default'),
                        )

            # ensure combo defaults are effectively applied for this tab (only empty values are updated)
            self._apply_combo_defaults_for_group(config_id, schema_options)

        # 4) Recompute mapping fully based on actual tabs and their 'agent_id' properties.
        self._rebuild_tab_index_mapping()

        # 5) Update visibility according to current mode/provider.
        self.toggle_extra_options_by_provider()

    def append_default_prompt(self):
        """Append default prompt to the preset editor"""
        mode = self.window.core.config.get('mode')
        if mode not in [
            MODE_AGENT_OPENAI,
            MODE_AGENT_LLAMA
        ]:
            return

        parent_key = ""
        if mode == MODE_AGENT_OPENAI:
            parent_key = "agent_provider_openai"
        elif mode == MODE_AGENT_LLAMA:
            parent_key = "agent_provider"

        # get current provider
        current_provider = self.window.controller.config.get_value(
            parent_id=self.id,
            key=parent_key,
            option=self.options[parent_key],
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

    def update_providers_list(self):
        """Update providers list in the preset editor"""
        self.window.ui.config[self.id]['agent_provider'].set_keys(
            self.window.controller.config.placeholder.apply_by_id('agent_provider_llama')
        )
        self.window.ui.config[self.id]['agent_provider_openai'].set_keys(
            self.window.controller.config.placeholder.apply_by_id('agent_provider_openai')
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
        elif key in ["agent_provider_openai", "agent_provider"]:
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

    def reload_all(self, all: bool = False):
        """
        Reload all data in the preset editor

        :param all: reload all custom agent options
        """
        self.update_providers_list()
        if all:
            self.reload_all_custom_agent_options()
            if self.opened:
                self.init(self.current_id)
    def init(self, id: Optional[str] = None):
        """
        Initialize preset editor

        :param id: preset id (filename)
        """
        self.opened = True
        self.current_id = id
        self.reload_all()

        data = PresetItem()
        data.name = ""
        data.filename = ""

        if id is None:
            self.experts.update_list()
            self.window.ui.config[self.id]['idx'].set_value("_")  # reset idx combo if new preset

        if id is not None and id != "":
            if id in self.window.core.presets.items:
                data = self.window.core.presets.items[id]
                data.filename = id
                self.current = data.uuid
        else:
            self.load_extra_defaults()

        mode = self.window.core.config.get("mode")
        if mode in [MODE_AGENT_OPENAI, MODE_AGENT_LLAMA]:
            self.reload_all_custom_agent_options()

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
            if mode == MODE_CHAT:
                data.chat = True
            elif mode == MODE_COMPLETION:
                data.completion = True
            elif mode == MODE_IMAGE:
                data.img = True
            # elif mode == MODE_VISION:
                # data.vision = True
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

        # toggle extra options
        self.toggle_extra_options()

        # update experts list, after ID loaded
        self.experts.update_list()

        # setup avatar config
        self.update_avatar_config(data)

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
        Save preset

        :param force: force overwrite file
        :param close: close dialog
        """
        preset_id = self.window.controller.config.get_value(
            parent_id=self.id,
            key="filename",
            option=self.options["filename"],
        )
        mode = self.window.core.config.get("mode")
        modes = [
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_IMAGE,
            # MODE_VISION,
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
        if preset_id == "current." + mode:
            self.window.ui.dialogs.alert("Reserved ID. Please use another ID.")
            return

        if preset_id is None or preset_id == "":
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
            preset_id = self.window.controller.presets.make_filename(name)
            path = os.path.join(
                self.window.core.config.path,
                "presets",
                preset_id + ".json",
            )
            if os.path.exists(path) and not force:
                preset_id += '_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        # validate filename
        preset_id = self.window.controller.presets.validate_filename(preset_id)
        is_new = False
        if preset_id not in self.window.core.presets.items:
            is_new = True
            self.window.core.presets.items[preset_id] = self.window.core.presets.build()
        elif not force:
            self.window.ui.dialogs.confirm(
                type='preset_exists',
                id=preset_id,
                msg=trans('confirm.preset.overwrite'),
            )
            return

        # check if at least one mode is selected
        is_mode = False
        get_value = self.window.controller.config.get_value
        for check in modes:
            if get_value(
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
        self.assign_data(preset_id)

        if is_new:
            # assign tmp avatar
            if self.tmp_avatar is not None:
                self.window.core.presets.items[preset_id].ai_avatar = self.tmp_avatar
                self.tmp_avatar = None
        else:
            self.tmp_avatar = None

        # if agent, assign experts and select only agent mode
        curr_mode = self.window.core.config.get('mode')
        if curr_mode == MODE_AGENT:
            itm = self.window.core.presets.items[preset_id]
            itm.reset_modes()
            itm.agent = True
        elif curr_mode == MODE_AGENT_LLAMA:
            itm = self.window.core.presets.items[preset_id]
            itm.reset_modes()
            itm.agent_llama = True
        elif curr_mode == MODE_AGENT_OPENAI:
            itm = self.window.core.presets.items[preset_id]
            itm.reset_modes()
            itm.agent_openai = True

        # apply changes to current active preset
        current = self.window.core.config.get('preset')
        if current is not None and current == preset_id:
            self.to_current(self.window.core.presets.items[preset_id])
            self.window.core.config.save()

        # update current uuid
        self.current = self.window.core.presets.items[preset_id].uuid

        # save
        no_scroll = False
        if not is_new:
            no_scroll = True
        self.window.core.presets.save(preset_id)
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
                value=preset_id,
            )
        self.window.update_status(trans('status.preset.saved'))

        # sort by name
        self.window.core.presets.sort_by_name()

        # switch to editing preset on save
        self.window.controller.presets.set(mode, preset_id)
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
        get_value = self.window.controller.config.get_value
        data_dict = {}
        for key in self.options:
            if key == "tool.function":
                continue  # assigned separately
            data_dict[key] = get_value(
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

        # extra options
        self.append_extra_options(preset)

        # avatar update
        self.update_avatar_config(preset)

    def to_current(self, preset: PresetItem):
        """
        Update preset field from editor

        :param preset: preset item
        """
        config = self.window.core.config
        config.set('ai_name', preset.ai_name)
        config.set('user_name', preset.user_name)
        config.set('prompt', preset.prompt)
        config.set('temperature', preset.temperature)

    @Slot()
    def from_current(self):
        """Copy data from current active preset"""
        apply_value = self.window.controller.config.apply_value
        get_config = self.window.core.config.get
        apply_value(
            parent_id=self.id,
            key="ai_name",
            option=self.options["ai_name"],
            value=get_config('ai_name'),
        )
        apply_value(
            parent_id=self.id,
            key="user_name",
            option=self.options["user_name"],
            value=get_config('user_name'),
        )
        apply_value(
            parent_id=self.id,
            key="prompt",
            option=self.options["prompt"],
            value=get_config('prompt'),
        )
        apply_value(
            parent_id=self.id,
            key="temperature",
            option=self.options["temperature"],
            value=get_config('temperature'),
        )
        apply_value(
            parent_id=self.id,
            key="model",
            option=self.options["model"],
            value=get_config('model'),
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

        avatar_widget = self.window.ui.nodes['preset.editor.avatar']

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
            avatar_widget.load_avatar(avatar_path)
            avatar_widget.enable_remove_button(True)
        return avatar_path

    def update_avatar_config(self, preset: PresetItem):
        """
        Update avatar config for preset

        :param preset: preset item
        """
        avatar_widget = self.window.ui.nodes['preset.editor.avatar']
        avatar_path = preset.ai_avatar
        if avatar_path:
            file_path = os.path.join(
                self.window.core.config.get_user_dir("presets"),
                "avatars",
                avatar_path,
            )
            if not os.path.exists(file_path):
                avatar_widget.remove_avatar()
                print("Avatar file does not exist:", file_path)
                return
            avatar_widget.load_avatar(file_path)
            avatar_widget.enable_remove_button(True)
        else:
            avatar_widget.remove_avatar()

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

    def toggle_tab(self, name: str, show: bool = True):
        """
        Show experts tab

        :param name: name of the tab
        :param show: Show or hide experts tab
        """
        tabs = self.window.ui.tabs['preset.editor.tabs']
        idx = self.TAB_IDX[name]
        if tabs is not None:
            if show:
                tabs.setTabEnabled(idx, True)
                tabs.setTabVisible(idx, True)
                self.experts.update_tab()
            else:
                tabs.setTabEnabled(idx, False)
                tabs.setTabVisible(idx, False)

    def reload_all_custom_agent_options(self, purge_missing_from_preset: bool = False):
        """
        Full, safe rebuild of all agent-specific option tabs.

        When to use:
        - Call this at editor opening or whenever multiple agent configs may have changed at once.

        What it does:
        - Updates provider combos (in case providers changed).
        - Removes ALL existing "agent extra" tabs (keeps base prompt tab at index 0).
        - Removes all UI config groups prefixed with 'agent.' (will be rebuilt).
        - Rebuilds tabs from the current provider registry order (provider.all()).
        - Applies saved values from current preset.extra[agent_id] when available; otherwise applies defaults.
        - Recomputes self.tab_options_idx from the real QTabWidget.
        - Restores visibility according to current mode/provider.

        Notes:
        - Must be called in the Qt GUI thread.
        - Does not persist changes to preset files; it's a UI rebuild.
        - Set purge_missing_from_preset=True if you also want to drop missing agents from preset.extra.
        """
        tabs = self.window.ui.tabs['preset.editor.extra']
        if not tabs:
            return

        # 0) Provider combos might need to be refreshed (e.g., new agents installed)
        self.update_providers_list()

        # Make sure existing tabs have agent_id metadata (for older builds).
        self._ensure_agent_tab_properties()

        mode = self.window.core.config.get('mode')
        exclude_ids = ["__prompt__"]

        # 1) Snapshot saved values from current preset (if any)
        preset = self.window.core.presets.get_by_uuid(self.current)
        saved_all = {}
        if preset and preset.extra:
            # expected: preset.extra[agent_id][option_tab_id][key] = value
            # shallow copy is sufficient (we only read and apply)
            for a_id, data in preset.extra.items():
                if isinstance(data, dict):
                    saved_all[a_id] = dict(data)

        # 2) Freeze UI to avoid flicker while we rebuild
        tabs.setUpdatesEnabled(False)
        try:
            # 3) Remove all agent extra tabs (keep base prompt at 0)
            for i in range(tabs.count() - 1, 1 - 1, -1):
                w = tabs.widget(i)
                if w is None:
                    continue
                if w.property('agent_id'):
                    tabs.removeTab(i)
                    w.deleteLater()

            # 4) Remove all UI config groups for agents (they will be re-created)
            cfg = self.window.ui.config
            for key in list(cfg.keys()):
                if isinstance(key, str) and key.startswith('agent.'):
                    try:
                        del cfg[key]
                    except Exception:
                        pass

            # 5) Optionally purge preset.extra entries for missing agents
            agents_dict = self.window.core.agents.provider.all() or {}
            existing_ids = set(agents_dict.keys())
            if purge_missing_from_preset and preset and isinstance(preset.extra, dict):
                for a_id in list(preset.extra.keys()):
                    if a_id not in existing_ids:
                        try:
                            del preset.extra[a_id]
                        except Exception:
                            pass
                # You may call self.window.core.presets.save(preset.filename) later if you want to persist.

            # 6) Rebuild tabs from current registry, in a deterministic order
            build_option_widgets = self.window.ui.dialogs.preset.build_option_widgets
            apply_value = self.window.controller.config.apply_value

            insertion_index = 1  # index 0 is the base prompt
            for a_id, agent in agents_dict.items():
                if not agent:
                    continue
                option_tabs = agent.get_options() or {}
                if not option_tabs:
                    # agent with no custom tabs -> only base prompt applies
                    continue

                for option_tab_id, option_desc in option_tabs.items():
                    if option_tab_id in exclude_ids:
                        continue

                    title = option_desc.get('label', '')
                    schema_options = option_desc.get('options', {}) or {}
                    config_id = f"agent.{a_id}.{option_tab_id}"

                    # Build UI widgets for this option group
                    widgets, options_layouts = build_option_widgets(config_id, schema_options)

                    # Layout: non-bool vertically, bools grouped in bottom row
                    layout = QVBoxLayout()
                    layout.setContentsMargins(0, 10, 0, 10)
                    checkbox_layout = QHBoxLayout()
                    for key, opt_layout in options_layouts.items():
                        opt_schema = schema_options.get(key, {})
                        if opt_schema.get('type') == 'bool':
                            checkbox_layout.addLayout(opt_layout)
                        else:
                            layout.addLayout(opt_layout)
                    layout.addStretch(1)
                    layout.addLayout(checkbox_layout)

                    # Create tab widget wrapped in a scroll area and tag with metadata
                    tab_content = QWidget()
                    tab_content.setLayout(layout)

                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setFrameShape(QFrame.NoFrame)
                    scroll.setWidget(tab_content)
                    scroll.setProperty('agent_id', a_id)
                    scroll.setProperty('option_tab_id', option_tab_id)

                    # Insert tab and advance anchor
                    insertion_index = min(insertion_index, tabs.count())
                    tabs.insertTab(insertion_index, scroll, title)
                    insertion_index += 1

                    # Apply saved values (if present) or defaults
                    saved_agent = saved_all.get(a_id, {})
                    saved_tab = saved_agent.get(option_tab_id, {}) if isinstance(saved_agent, dict) else {}

                    for key, opt_schema in schema_options.items():
                        if key in saved_tab:
                            apply_value(
                                parent_id=config_id,
                                key=key,
                                option=opt_schema,
                                value=saved_tab[key],
                            )
                        elif 'default' in opt_schema:
                            apply_value(
                                parent_id=config_id,
                                key=key,
                                option=opt_schema,
                                value=opt_schema.get('default'),
                            )

                    # ensure combo defaults are effectively applied for this tab (only empty values are updated)
                    self._apply_combo_defaults_for_group(config_id, schema_options)

            # 7) Recompute the index mapping strictly from the QTabWidget
            self._rebuild_tab_index_mapping()

            # 8) Restore proper visibility for the current mode/provider
            self.toggle_extra_options_by_provider()

        finally:
            tabs.setUpdatesEnabled(True)

    # ---------- Helpers for reliable combo defaults in agent extra options ----------

    def _apply_combo_defaults_for_group(self, parent_id: str, schema_options: Dict[str, Any]) -> None:
        """
        Ensure that combo-type inputs inside a given UI config group have their default values applied
        when the current value is empty ("", None or "_"). This avoids the situation where combo boxes
        remain uninitialized while other field types receive defaults correctly.

        This function never overrides a non-empty value set by the user or loaded from a preset.
        """
        if not schema_options:
            return

        get_value = self.window.controller.config.get_value
        apply_value = self.window.controller.config.apply_value

        for key, opt_schema in schema_options.items():
            if not isinstance(opt_schema, dict):
                continue
            if opt_schema.get('type') != 'combo':
                continue

            default_val = opt_schema.get('default', None)
            if default_val is None:
                continue

            current_val = get_value(
                parent_id=parent_id,
                key=key,
                option=opt_schema,
            )

            # Treat "_", "", None as empty and safe to replace with default
            if current_val in (None, "", "_"):
                # First try apply_value (standard path)
                apply_value(
                    parent_id=parent_id,
                    key=key,
                    option=opt_schema,
                    value=default_val,
                )
                # Additionally set directly on widget if accessible to guard against timing of key population
                try:
                    widget_group = self.window.ui.config.get(parent_id, {})
                    widget = widget_group.get(key)
                    if widget and hasattr(widget, "set_value"):
                        widget.set_value(default_val)
                except Exception:
                    # Silent fallback; apply_value above should already handle most cases
                    pass