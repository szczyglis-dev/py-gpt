#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

import os
import re

from ..utils import trans


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
        data['vision'] = False
        data['langchain'] = False
        data['assistant'] = False
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
            elif mode == 'vision':
                data['vision'] = True
            elif mode == 'langchain':
                data['langchain'] = True
            elif mode == 'assistant':
                data['assistant'] = True

        self.config_change('preset.filename', data['filename'], 'preset.editor')
        self.config_change('preset.ai_name', data['ai_name'], 'preset.editor')
        self.config_change('preset.user_name', data['user_name'], 'preset.editor')
        self.config_change('preset.prompt', data['prompt'], 'preset.editor')
        self.config_change('preset.name', data['name'], 'preset.editor')
        self.config_slider('preset.temperature', data['temperature'], '', 'preset.editor')
        self.config_toggle('preset.img', data['img'], 'preset.editor')
        self.config_toggle('preset.chat', data['chat'], 'preset.editor')
        if 'completion' in data:
            self.config_toggle('preset.completion', data['completion'], 'preset.editor')
        if 'vision' in data:
            self.config_toggle('preset.vision', data['vision'], 'preset.editor')
        if 'langchain' in data:
            self.config_toggle('preset.langchain', data['langchain'], 'preset.editor')
        if 'assistant' in data:
            self.config_toggle('preset.assistant', data['assistant'], 'preset.editor')

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

        # validate filename
        preset = self.validate_filename(preset)
        if preset not in self.window.config.presets:
            self.window.config.presets[preset] = {}

        # prepare path
        filepath = os.path.join(self.window.config.path, 'presets', preset + '.json')

        # if exists then show confirmation dialog
        if os.path.exists(filepath) and not force:
            self.window.ui.dialogs.confirm('preset_exists', preset, trans('confirm.preset.overwrite'))
            return

        # check if at least one mode is enabled
        is_chat = self.window.config_option['preset.chat'].box.isChecked()
        is_completion = self.window.config_option['preset.completion'].box.isChecked()
        is_img = self.window.config_option['preset.img'].box.isChecked()
        is_vision = self.window.config_option['preset.vision'].box.isChecked()
        is_langchain = self.window.config_option['preset.langchain'].box.isChecked()
        is_assistant = self.window.config_option['preset.assistant'].box.isChecked()

        # if not chat or completion then show warning
        if not is_chat and not is_completion and not is_img and not is_vision and not is_langchain and not is_assistant:
            self.window.ui.dialogs.alert(trans('alert.preset.no_chat_completion'))
            return

        # assign data from fields to preset
        self.assign_data(preset)

        # save file
        self.window.config.save_preset(preset)
        self.window.controller.model.update()

        self.window.ui.dialogs.close('editor.preset.presets')
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
        self.window.config.presets[preset]['vision'] = self.window.config_option['preset.vision'].box.isChecked()
        self.window.config.presets[preset]['langchain'] = self.window.config_option['preset.langchain'].box.isChecked()
        self.window.config.presets[preset]['assistant'] = self.window.config_option['preset.assistant'].box.isChecked()

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
                    self.window.set_status(trans('status.preset.deleted'))

    def from_current(self):
        """Loads from current prompt"""
        self.config_change('preset.ai_name', self.window.config.data['ai_name'], 'preset.editor')
        self.config_change('preset.user_name', self.window.config.data['user_name'],
                           'preset.editor')
        self.config_change('preset.prompt', self.window.config.data['prompt'], 'preset.editor')
        self.config_slider('preset.temperature', self.window.config.data['temperature'], '',
                           'preset.editor')

    def use(self):
        """Copies preset prompt to input"""
        self.window.controller.input.append(self.window.data['preset.prompt'].toPlainText())

    def validate_filename(self, value):
        """
        Validates filename

        :param value: filename
        :return: sanitized filename
        """
        # strip not allowed characters
        return re.sub(r'[^\w\s-]', '', value)

    def config_toggle(self, id, value, section=None):
        """
        Toggles checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        preset = self.window.config.data['preset']  # current preset
        is_current = True
        if section == 'preset.editor':
            preset = self.window.config_option['preset.filename'].text()  # editing preset
            is_current = False
        self.update_field(id, value, preset, is_current)
        self.window.config_option[id].box.setChecked(value)

    def config_change(self, id, value, section=None):
        """
        Changes input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        # validate filename
        if id == 'preset.filename':
            value = self.validate_filename(value)
            self.window.config_option[id].setText(value)

        preset = self.window.config.data['preset']  # current preset
        is_current = True
        if section == 'preset.editor':
            preset = self.window.config_option['preset.filename'].text()  # editing preset
            is_current = False
        self.update_field(id, value, preset, is_current)
        self.window.config_option[id].setText('{}'.format(value))

    def config_slider(self, id, value, type=None, section=None):
        """
        Applies slider + input value

        :param id: option id
        :param value: option value
        :param type: option type (slider, input, None)
        :param section: option section (settings, preset.editor, None)
        """
        # temperature
        multiplier = 100
        if type != 'slider':
            try:
                value = float(value)
            except:
                value = 0.0
                self.window.config_option[id].input.setText(str(value))
            if value < 0:
                value = 0.0
            elif value > 2:
                value = 2.0
            self.window.config_option[id].input.setText(str(value))

        slider_value = round(float(value) * multiplier, 0)
        input_value = value
        if type == 'slider':
            input_value = value / multiplier

        preset = self.window.config.data['preset']  # current preset
        is_current = True
        if section == 'preset.editor':
            preset = self.window.config_option['preset.filename'].text()  # editing preset
            is_current = False
        self.update_field(id, input_value, preset, is_current)

        # update from slider
        if type == 'slider':
            txt = '{}'.format(input_value)
            self.window.config_option[id].input.setText(txt)

        # update from input
        elif type == 'input':
            if slider_value < 1:
                slider_value = 1
            elif slider_value > 200:
                slider_value = 200
            self.window.config_option[id].slider.setValue(slider_value)

        # update from raw value
        else:
            txt = '{}'.format(value)
            self.window.config_option[id].input.setText(txt)
            self.window.config_option[id].slider.setValue(slider_value)
