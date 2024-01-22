#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 10:00:00                  #
# ================================================== #

import re

from pygpt_net.controller.presets.editor import Editor
from pygpt_net.utils import trans


class Presets:
    def __init__(self, window=None):
        """
        Presets controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)

    def setup(self):
        """Setup presets"""
        self.editor.setup()

    def select(self, idx: int):
        """
        Select preset

        :param idx: value of the list (row idx)
        """
        # check if preset change is not locked
        if self.preset_change_locked():
            return
        mode = self.window.core.config.get('mode')
        self.set_by_idx(mode, idx)

        # update all layout
        self.window.controller.ui.update()

    def use(self):
        """Copy preset prompt to input"""
        self.window.controller.chat.common.append_to_input(self.window.ui.nodes['preset.prompt'].toPlainText())

    def set(self, mode, preset):
        """
        Set preset

        :param mode: mode name
        :param preset: preset name
        """
        if not self.window.core.presets.has(mode, preset):
            return False
        self.window.core.config.data['preset'] = preset
        if 'current_preset' not in self.window.core.config.data:
            self.window.core.config.data['current_preset'] = {}
        self.window.core.config.data['current_preset'][mode] = preset

    def set_by_idx(self, mode: str, idx: int):
        """
        Set preset by index

        :param mode: mode name
        :param idx: preset index
        """
        preset = self.window.core.presets.get_by_idx(idx, mode)
        self.window.core.config.data['preset'] = preset
        if 'current_preset' not in self.window.core.config.data:
            self.window.core.config.data['current_preset'] = {}
        self.window.core.config.data['current_preset'][mode] = preset

        # select model
        self.select_model()

    def select_current(self):
        """Select preset by current"""
        mode = self.window.core.config.get('mode')
        preset = self.window.core.config.get('preset')
        items = self.window.core.presets.get_by_mode(mode)
        if preset in items:
            idx = list(items.keys()).index(preset)
            current = self.window.ui.models['preset.presets'].index(idx, 0)
            self.window.ui.nodes['preset.presets'].setCurrentIndex(current)

    def select_default(self):
        """Set default preset"""
        preset = self.window.core.config.get('preset')
        if preset is None or preset == "":
            mode = self.window.core.config.get('mode')

            # set previous selected preset
            current = self.window.core.config.get('current_preset')  # dict of modes, one preset per mode
            if mode in current and \
                    current[mode] is not None and \
                    current[mode] != "" and \
                    current[mode] in self.window.core.presets.get_by_mode(mode):
                self.window.core.config.set('preset', current[mode])
            else:
                # or set default preset
                self.window.core.config.set('preset', self.window.core.presets.get_default(mode))

    def update_data(self):
        """Update preset data"""
        id = self.window.core.config.get('preset')
        if id is None or id == "":
            self.reset()  # clear preset fields
            self.window.controller.mode.reset_current()
            return

        if id not in self.window.core.presets.items:
            self.window.core.config.set('preset', "")  # clear preset if not found
            self.reset()  # clear preset fields
            self.window.controller.mode.reset_current()
            return

        # update preset fields
        data = self.window.core.presets.items[id]
        self.window.ui.nodes['preset.prompt'].setPlainText(data.prompt)
        # self.window.ui.nodes['preset.ai_name'].setText(data.ai_name)
        # self.window.ui.nodes['preset.user_name'].setText(data.user_name)

        # update current data
        self.window.core.config.set('prompt', data.prompt)
        self.window.core.config.set('ai_name', data.ai_name)
        self.window.core.config.set('user_name', data.user_name)

    def update_current(self):
        """Update current mode, model and preset"""
        mode = self.window.core.config.get('mode')
        id = self.window.core.config.get('preset')
        if id is not None and id != "":
            if id in self.window.core.presets.items:
                preset = self.window.core.presets.items[id]
                self.window.core.config.set('user_name', preset.user_name)
                self.window.core.config.set('ai_name', preset.ai_name)
                self.window.core.config.set('prompt', preset.prompt)
                self.window.core.config.set('temperature', preset.temperature)
                return

        self.window.core.config.set('user_name', None)
        self.window.core.config.set('ai_name', None)
        self.window.core.config.set('temperature', 1.0)

        # set default prompt if mode is chat
        if mode == 'chat':
            self.window.core.config.set('prompt', self.window.core.config.get('default_prompt'))
        else:
            self.window.core.config.set('prompt', None)

    def from_global(self):
        """Update current preset from global prompt"""
        id = self.window.core.config.get('preset')
        if id is not None and id != "":
            if id in self.window.core.presets.items:
                preset = self.window.core.presets.items[id]
                preset.prompt = self.window.core.config.get('prompt')
                self.window.core.presets.save(preset)

    def select_model(self):
        """Select model by current preset"""
        mode = self.window.core.config.get('mode')
        id = self.window.core.config.get('preset')
        if id is not None and id != "":
            if id in self.window.core.presets.items:
                preset = self.window.core.presets.items[id]
                if preset.model is not None and preset.model != "" and preset.model != "_":
                    if preset.model in self.window.core.models.items:
                        if self.window.core.models.has(preset.model) \
                                and self.window.core.models.is_allowed(preset.model, mode):
                            self.window.core.config.set('model', preset.model)
                            self.window.controller.model.set(mode, preset.model)
                            self.window.controller.model.update_list()
                            self.window.controller.model.select_current()

    def refresh(self):
        """Refresh presets"""
        self.select_default()
        self.update_current()
        self.update_data()
        self.window.controller.mode.update_temperature()
        self.update_list()
        self.select_current()

    def update_list(self):
        """Update presets list"""
        mode = self.window.core.config.get('mode')
        items = self.window.core.presets.get_by_mode(mode)
        self.window.ui.toolbox.presets.update(items)

    def reset(self):
        """Reset preset data"""
        self.window.ui.nodes['preset.prompt'].setPlainText("")
        # self.window.ui.nodes['preset.ai_name'].setText("")
        # self.window.ui.nodes['preset.user_name'].setText("")

    def make_filename(self, name: str) -> str:
        """
        Make preset filename from name

        :param name: preset name
        :return: preset filename
        """
        filename = name.lower()
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        return filename

    def duplicate(self, idx: int = None):
        """
        Duplicate preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset = self.window.core.presets.get_by_idx(idx, mode)
            if preset is not None and preset != "":
                if preset in self.window.core.presets.items:
                    new_id = self.window.core.presets.duplicate(preset)
                    self.window.core.config.set('preset', new_id)
                    self.refresh()
                    idx = self.window.core.presets.get_idx_by_id(mode, new_id)
                    self.editor.edit(idx)
                    self.window.ui.status(trans('status.preset.duplicated'))

    def clear(self, force: bool = False):
        """
        Clear preset data

        :param force: force clear data
        """
        preset = self.window.core.config.get('preset')

        if not force:
            self.window.ui.dialogs.confirm('preset_clear', '', trans('confirm.preset.clear'))
            return

        self.window.core.config.set('prompt', "")
        self.window.core.config.set('ai_name', "")
        self.window.core.config.set('user_name', "")
        self.window.core.config.set('temperature', 1.0)

        if preset is not None and preset != "":
            if preset in self.window.core.presets.items:
                self.window.core.presets.items[preset].ai_name = ""
                self.window.core.presets.items[preset].user_name = ""
                self.window.core.presets.items[preset].prompt = ""
                self.window.core.presets.items[preset].temperature = 1.0
                self.refresh()

        self.window.ui.status(trans('status.preset.cleared'))

    def delete(self, idx: int = None, force: bool = False):
        """
        Delete preset

        :param idx: preset index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset = self.window.core.presets.get_by_idx(idx, mode)
            if preset is not None and preset != "":
                if preset in self.window.core.presets.items:
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('preset_delete', idx, trans('confirm.preset.delete'))
                        return

                    if preset == self.window.core.config.get('preset'):
                        self.window.core.config.set('preset', None)
                    self.window.core.presets.remove(preset, True)
                    self.refresh()
                    self.window.ui.status(trans('status.preset.deleted'))

    def validate_filename(self, value: str) -> str:
        """
        Validate filename

        :param value: filename
        :return: sanitized filename
        """
        # strip not allowed characters
        return re.sub(r'[^\w\s-]', '', value)

    def preset_change_locked(self) -> bool:
        """
        Check if preset change is locked

        :return: True if locked
        """
        # if self.window.controller.chat.input.generating:
        # return True
        return False
