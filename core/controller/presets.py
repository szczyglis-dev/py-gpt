#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

import os
import re

from core.utils import trans


class Presets:
    def __init__(self, window=None):
        """
        Presets controller

        :param window: main window object
        """
        self.window = window

    def update_field(self, id, value, preset=None, current=False):
        """
        Updates preset field from editor

        :param id: field id
        :param value: field value
        :param preset: preset name (ID / filename)
        :param current: if True, updates current preset
        """
        if preset is not None and preset != "":
            if preset in self.window.config.presets:
                if id == 'preset.ai_name':
                    self.window.config.presets[preset]['ai_name'] = value
                elif id == 'preset.user_name':
                    self.window.config.presets[preset]['user_name'] = value
                elif id == 'preset.prompt':
                    self.window.config.presets[preset]['prompt'] = value
                elif id == 'preset.temperature' or id == 'current_temperature':
                    self.window.config.presets[preset]['temperature'] = float(value)

        # update current data
        if current:
            if id == 'preset.ai_name':
                self.window.config.data['ai_name'] = value
            elif id == 'preset.user_name':
                self.window.config.data['user_name'] = value
            elif id == 'preset.prompt':
                self.window.config.data['prompt'] = value
            elif id == 'preset.temperature' or id == 'current_temperature':
                self.window.config.data['temperature'] = float(value)

        self.window.controller.ui.update()

    def edit(self, idx=None):
        """
        Opens preset editor

        :param idx: preset index (row index)
        """
        preset = None
        if idx is not None:
            mode = self.window.config.data['mode']
            preset = self.window.config.get_preset_by_idx(idx, mode)

        self.init_editor(preset)
        self.window.ui.dialogs.open_editor('editor.preset.presets', idx)

    def init_editor(self, preset=None):
        """
        Initializes preset editor

        :param preset: preset name (ID / filename)
        """
        data = {}
        data['ai_name'] = ""
        data['user_name'] = ""
        data['prompt'] = ""
        data['temperature'] = 1.0
        data['img'] = False
        data['chat'] = False
        data['completion'] = False
        data['name'] = ""
        data['filename'] = ""

        if preset is not None and preset != "":
            if preset in self.window.config.presets:
                data = self.window.config.presets[preset]
                data['filename'] = preset

        if data['name'] is None:
            data['name'] = ""
        if data['ai_name'] is None:
            data['ai_name'] = ""
        if data['user_name'] is None:
            data['user_name'] = ""
        if data['prompt'] is None:
            data['prompt'] = ""
        if data['filename'] is None:
            data['filename'] = ""

        if preset is None:
            mode = self.window.config.data['mode']
            if mode == 'chat':
                data['chat'] = True
            elif mode == 'completion':
                data['completion'] = True
            elif mode == 'img':
                data['img'] = True

        self.window.controller.settings.change('preset.filename', data['filename'], 'preset.editor')
        self.window.controller.settings.change('preset.ai_name', data['ai_name'], 'preset.editor')
        self.window.controller.settings.change('preset.user_name', data['user_name'], 'preset.editor')
        self.window.controller.settings.change('preset.prompt', data['prompt'], 'preset.editor')
        self.window.controller.settings.change('preset.name', data['name'], 'preset.editor')
        self.window.controller.settings.apply('preset.temperature', data['temperature'], '', 'preset.editor')
        self.window.controller.settings.toggle('preset.img', data['img'], 'preset.editor')
        self.window.controller.settings.toggle('preset.chat', data['chat'], 'preset.editor')
        self.window.controller.settings.toggle('preset.completion', data['completion'], 'preset.editor')

    def save(self, force=False):
        """
        Saves preset

        :param force: force overwrite file
        """
        preset = self.window.config_option['preset.filename'].text()
        if preset is None or preset == "" or preset.startswith('current.'):
            self.window.ui.dialogs.alert(trans('alert.preset.empty_id'))
            self.window.set_status(trans('status.preset.empty_id'))
            return

        preset = self.window.controller.presets.validate_filename(preset)

        if preset not in self.window.config.presets:
            self.window.config.presets[preset] = {}

        filepath = os.path.join(self.window.config.path, 'presets', preset + '.json')

        # if exists then show confirmation dialog
        if os.path.exists(filepath) and not force:
            self.window.ui.dialogs.confirm('preset_exists', preset, trans('confirm.preset.overwrite'))
            return

        # check if at least one mode is enabled
        is_chat = self.window.config_option['preset.chat'].box.isChecked()
        is_completion = self.window.config_option['preset.completion'].box.isChecked()
        is_img = self.window.config_option['preset.img'].box.isChecked()

        # if not chat or completion then show warning
        if not is_chat and not is_completion and not is_img:
            self.window.ui.dialogs.alert(trans('alert.preset.no_chat_completion'))
            return

        # assign data from fields to preset
        self.assign_data(preset)

        # save file
        self.window.config.save_preset(preset)
        self.window.controller.model.update()

        self.window.ui.dialogs.close('editor.preset.presets')
        filepath = os.path.join(self.window.config.path, 'presets', preset + '.json')
        self.window.set_status(trans('status.preset.saved'))

    def assign_data(self, preset):
        """
        Assigns data from fields to preset

        :param preset: preset name (ID / filename)
        """
        name = self.window.config_option['preset.name'].text()
        if name is None or name == "":
            name = preset + " " + trans('preset.untitled')
        self.window.config.presets[preset]['name'] = name
        self.window.config.presets[preset]['ai_name'] = self.window.config_option['preset.ai_name'].text()
        self.window.config.presets[preset]['user_name'] = self.window.config_option['preset.user_name'].text()
        self.window.config.presets[preset]['prompt'] = self.window.config_option['preset.prompt'].toPlainText()
        self.window.config.presets[preset]['temperature'] = float(
            self.window.config_option['preset.temperature'].input.text())
        self.window.config.presets[preset]['img'] = self.window.config_option['preset.img'].box.isChecked()
        self.window.config.presets[preset]['chat'] = self.window.config_option['preset.chat'].box.isChecked()
        self.window.config.presets[preset]['completion'] = self.window.config_option[
            'preset.completion'].box.isChecked()

    def duplicate(self, idx=None):
        """
        Duplicates preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            mode = self.window.config.data['mode']
            preset = self.window.config.get_preset_by_idx(idx, mode)
            if preset is not None and preset != "":
                if preset in self.window.config.presets:
                    new_id = self.window.config.duplicate_preset(preset)
                    self.window.config.data['preset'] = new_id
                    self.window.controller.model.update()
                    idx = self.window.config.get_preset_idx(mode, new_id)
                    self.edit(idx)
                    self.window.set_status(trans('status.preset.duplicated'))

    def clear(self, force=False):
        """
        Clears preset data

        :param force: force clear data
        """
        preset = self.window.config.data['preset']

        if not force:
            self.window.ui.dialogs.confirm('preset_clear', '', trans('confirm.preset.clear'))
            return

        self.window.config.data['prompt'] = ""
        self.window.config.data['ai_name'] = ""
        self.window.config.data['user_name'] = ""
        self.window.config.data['temperature'] = 1.0

        if preset is not None and preset != "":
            if preset in self.window.config.presets:
                self.window.config.presets[preset]['ai_name'] = ""
                self.window.config.presets[preset]['user_name'] = ""
                self.window.config.presets[preset]['prompt'] = ""
                self.window.config.presets[preset]['temperature'] = 1.0
                self.window.controller.model.update()

        self.window.set_status(trans('status.preset.cleared'))

    def delete(self, idx=None, force=False):
        """
        Deletes preset

        :param idx: preset index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            mode = self.window.config.data['mode']
            preset = self.window.config.get_preset_by_idx(idx, mode)
            if preset is not None and preset != "":
                if preset in self.window.config.presets:
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('preset_delete', idx, trans('confirm.preset.delete'))
                        return

                    if preset == self.window.config.data['preset']:
                        self.window.config.data['preset'] = None
                    self.window.config.delete_preset(preset, True)
                    self.window.controller.model.update()
                    path = os.path.join(self.window.config.path, 'presets', preset + '.json')
                    self.window.set_status(trans('status.preset.deleted'))

    def from_current(self):
        """Loads from current prompt"""
        self.window.controller.settings.change('preset.ai_name', self.window.config.data['ai_name'], 'preset.editor')
        self.window.controller.settings.change('preset.user_name', self.window.config.data['user_name'],
                                               'preset.editor')
        self.window.controller.settings.change('preset.prompt', self.window.config.data['prompt'], 'preset.editor')
        self.window.controller.settings.apply('preset.temperature', self.window.config.data['temperature'], '',
                                              'preset.editor')

    def use(self):
        """Copies preset prompt to input"""
        text = self.window.data['preset.prompt'].toPlainText()
        self.window.controller.input.append(text)

    def validate_filename(self, value):
        """
        Validates filename

        :param value: filename
        :return: validated filename
        """
        # strip not allowed characters
        value = re.sub(r'[^\w\s-]', '', value)
        return value
