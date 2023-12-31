#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
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

        :param id: preset id
        """
        data = PresetItem
        data.ai_name = ""
        data.user_name = ""
        data.prompt = ""
        data.temperature = 1.0
        data.img = False
        data.chat = False
        data.completion = False
        data.vision = False
        data.langchain = False
        data.assistant = False
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

        if id is None:
            mode = self.window.core.config.get('mode')
            if mode == 'chat':
                data.chat = True
            elif mode == 'completion':
                data.completion = True
            elif mode == 'img':
                data.img = True
            elif mode == 'vision':
                data.vision = True
            elif mode == 'langchain':
                data.langchain = True
            elif mode == 'assistant':
                data.assistant = True

        self.config_change('preset.filename', data.filename, 'preset.editor')
        self.config_change('preset.ai_name', data.ai_name, 'preset.editor')
        self.config_change('preset.user_name', data.user_name, 'preset.editor')
        self.config_change('preset.prompt', data.prompt, 'preset.editor')
        self.config_change('preset.name', data.name, 'preset.editor')
        self.config_slider('preset.temperature', data.temperature, '', 'preset.editor')

        self.config_toggle('preset.img', data.img, 'preset.editor')
        self.config_toggle('preset.chat', data.chat, 'preset.editor')
        self.config_toggle('preset.completion', data.completion, 'preset.editor')
        self.config_toggle('preset.vision', data.vision, 'preset.editor')
        self.config_toggle('preset.langchain', data.langchain, 'preset.editor')
        self.config_toggle('preset.assistant', data.assistant, 'preset.editor')

        # set focus to name field
        self.window.ui.config_option['preset.name'].setFocus()

    def save(self, force: bool = False):
        """
        Save preset

        :param force: force overwrite file
        """
        id = self.window.ui.config_option['preset.filename'].text()
        mode = self.window.core.config.get('mode')
        is_created = False

        # disallow editing current preset cache
        if id.startswith('current.'):
            return

        if id is None or id == "":
            name = self.window.ui.config_option['preset.name'].text()
            if name is None or name == "":
                self.window.ui.dialogs.alert(trans('alert.preset.empty_id'))
                self.window.ui.status(trans('status.preset.empty_id'))
                return
            # generate new filename
            id = self.window.controller.presets.make_filename(name)
            # check if not exists
            path = os.path.join(self.window.core.config.path, 'presets', id + '.json')
            if os.path.exists(path) and not force:
                # add datetime suffix to filename
                id = id + '_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            is_created = True

        # validate filename
        id = self.window.controller.presets.validate_filename(id)
        if id not in self.window.core.presets.items:
            self.window.core.presets.items[id] = PresetItem()
        elif not force:
            self.window.ui.dialogs.confirm('preset_exists', id, trans('confirm.preset.overwrite'))
            return

        # check if at least one mode is enabled
        is_chat = self.window.ui.config_option['preset.chat'].box.isChecked()
        is_completion = self.window.ui.config_option['preset.completion'].box.isChecked()
        is_img = self.window.ui.config_option['preset.img'].box.isChecked()
        is_vision = self.window.ui.config_option['preset.vision'].box.isChecked()
        is_langchain = self.window.ui.config_option['preset.langchain'].box.isChecked()
        is_assistant = self.window.ui.config_option['preset.assistant'].box.isChecked()

        # if any mode selected
        if not is_chat \
                and not is_completion \
                and not is_img \
                and not is_vision \
                and not is_langchain \
                and not is_assistant:
            self.window.ui.dialogs.alert(trans('alert.preset.no_chat_completion'))
            return

        # assign data from fields to preset
        self.assign_data(id)

        # save file
        self.window.core.presets.save(id)
        self.window.controller.presets.refresh()

        # close dialog
        self.window.ui.dialogs.close('editor.preset.presets')
        self.window.ui.status(trans('status.preset.saved'))

        # switch to editing preset
        self.window.controller.presets.set(mode, id)

        # sort by name
        self.window.core.presets.sort_by_name()

        # update list
        self.window.controller.presets.refresh()

    def assign_data(self, id: str):
        """
        Assign data from fields to preset

        :param id: preset id
        """
        name = self.window.ui.config_option['preset.name'].text()
        if name is None or name == "":
            name = id + " " + trans('preset.untitled')
        self.window.core.presets.items[id].name = name
        self.window.core.presets.items[id].ai_name = self.window.ui.config_option['preset.ai_name'].text()
        self.window.core.presets.items[id].user_name = self.window.ui.config_option['preset.user_name'].text()
        self.window.core.presets.items[id].prompt = self.window.ui.config_option['preset.prompt'].toPlainText()
        self.window.core.presets.items[id].temperature = float(
            self.window.ui.config_option['preset.temperature'].input.text())
        self.window.core.presets.items[id].img = self.window.ui.config_option['preset.img'].box.isChecked()
        self.window.core.presets.items[id].chat = self.window.ui.config_option['preset.chat'].box.isChecked()
        self.window.core.presets.items[id].completion = self.window.ui.config_option[
            'preset.completion'].box.isChecked()
        self.window.core.presets.items[id].vision = self.window.ui.config_option['preset.vision'].box.isChecked()
        self.window.core.presets.items[id].langchain = self.window.ui.config_option[
            'preset.langchain'].box.isChecked()
        self.window.core.presets.items[id].assistant = self.window.ui.config_option[
            'preset.assistant'].box.isChecked()

    def from_current(self):
        """Load from current prompt"""
        self.config_change('preset.ai_name', self.window.core.config.get('ai_name'), 'preset.editor')
        self.config_change('preset.user_name', self.window.core.config.get('user_name'),
                           'preset.editor')
        self.config_change('preset.prompt', self.window.core.config.get('prompt'), 'preset.editor')
        self.config_slider('preset.temperature', self.window.core.config.get('temperature'), '',
                           'preset.editor')

    def update_field(self, id: str, value: any, preset: str = None, current: any = False):
        """
        Update preset field from editor

        :param id: field id
        :param value: field value
        :param preset: preset name (ID / filename)
        :param current: if true, updates current preset
        """
        if preset is not None and preset != "":
            if preset in self.window.core.presets.items:
                if id == 'preset.ai_name':
                    self.window.core.presets.items[preset].ai_name = value
                elif id == 'preset.user_name':
                    self.window.core.presets.items[preset].user_name = value
                elif id == 'preset.prompt':
                    self.window.core.presets.items[preset].prompt = value
                elif id == 'preset.temperature' or id == 'current_temperature':
                    self.window.core.presets.items[preset].temperature = float(value)

        # update current data
        if current:
            if id == 'preset.ai_name':
                self.window.core.config.set('ai_name', value)
            elif id == 'preset.user_name':
                self.window.core.config.set('user_name', value)
            elif id == 'preset.prompt':
                self.window.core.config.set('prompt', value)
            elif id == 'preset.temperature' or id == 'current_temperature':
                self.window.core.config.set('temperature', float(value))

        self.window.controller.ui.update_tokens()

    def config_toggle(self, id: str, value: any, section: str = None):
        """
        Toggle checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        preset = self.window.core.config.get('preset')  # current preset
        is_current = True
        if section == 'preset.editor':
            preset = self.window.ui.config_option['preset.filename'].text()  # editing preset
            is_current = False
        self.update_field(id, value, preset, is_current)
        self.window.ui.config_option[id].box.setChecked(value)

    def config_change(self, id: str, value: any, section: str = None):
        """
        Change input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        # validate filename
        if id == 'preset.filename':
            value = self.window.controller.presets.validate_filename(value)
            self.window.ui.config_option[id].setText(value)

        preset = self.window.core.config.get('preset')  # current preset
        is_current = True
        if section == 'preset.editor':
            preset = self.window.ui.config_option['preset.filename'].text()  # editing preset
            is_current = False

        self.update_field(id, value, preset, is_current)
        self.window.ui.config_option[id].setText('{}'.format(value))

    def config_slider(self, id: str, value: any, type: str = None, section: str = None):
        """
        Apply slider + input value

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
                self.window.ui.config_option[id].input.setText(str(value))
            if value < 0:
                value = 0.0
            elif value > 2:
                value = 2.0
            self.window.ui.config_option[id].input.setText(str(value))

        slider_value = round(float(value) * multiplier, 0)
        input_value = value
        if type == 'slider':
            input_value = value / multiplier

        preset = self.window.core.config.get('preset')  # current preset
        is_current = True
        if section == 'preset.editor':
            preset = self.window.ui.config_option['preset.filename'].text()  # editing preset
            is_current = False
        self.update_field(id, input_value, preset, is_current)

        # update from slider
        if type == 'slider':
            txt = '{}'.format(input_value)
            self.window.ui.config_option[id].input.setText(txt)

        # update from input
        elif type == 'input':
            if slider_value < 1:
                slider_value = 1
            elif slider_value > 200:
                slider_value = 200
            self.window.ui.config_option[id].slider.setValue(slider_value)

        # update from raw value
        else:
            txt = '{}'.format(value)
            self.window.ui.config_option[id].input.setText(txt)
            self.window.ui.config_option[id].slider.setValue(slider_value)
