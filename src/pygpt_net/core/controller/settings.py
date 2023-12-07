#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.07 10:00:00                  #
# ================================================== #

import os

from showinfm import show_in_file_manager
from ..utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Settings controller

        :param window: main window object
        """
        self.window = window

    def save(self, id=None):
        """
        Saves settings

        :param id: settings id
        """
        if id == "settings":
            self.window.config.data['api_key'] = self.window.config_option['api_key'].text()
            self.window.config.data['organization_key'] = self.window.config_option['organization_key'].text()
            self.window.config.data['img_resolution'] = self.window.config_option['img_resolution'].text()
            self.window.config.data['ctx.auto_summary.system'] = self.window.config_option[
                'ctx.auto_summary.system'].text()
            self.window.config.data['ctx.auto_summary.prompt'] = self.window.config_option[
                'ctx.auto_summary.prompt'].toPlainText()

        info = trans('info.settings.saved')
        self.window.config.save()
        self.window.set_status(info)
        self.close_window(id)
        self.update_font_size()
        self.window.controller.ui.update()

    def save_all(self):
        """Saves all settings"""
        info = trans('info.settings.all.saved')
        self.window.config.save()
        self.window.config.save_presets()
        self.window.controller.notepad.save()
        self.window.ui.dialogs.alert(info)
        self.window.set_status(info)
        self.window.controller.ui.update()

    def start_settings(self):
        """Opens settings at first launch (no API key)"""
        self.toggle_settings('settings')
        self.window.ui.dialogs.close('info.start')

    def update_font_size(self):
        """Updates font size"""
        self.window.data['output'].setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.window.data['input'].setStyleSheet(self.window.controller.theme.get_style('chat_input'))
        self.window.data['ctx.contexts'].setStyleSheet(self.window.controller.theme.get_style('ctx.contexts'))
        self.window.data['notepad1'].setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.window.data['notepad2'].setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.window.data['notepad3'].setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.window.data['notepad4'].setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.window.data['notepad5'].setStyleSheet(self.window.controller.theme.get_style('chat_output'))

    def toggle_settings(self, id):
        """
        Toggles settings

        :param id: settings id
        """
        width = 500
        height = 600

        if id in self.window.settings.active and self.window.settings.active[id]:
            self.close_window(id)
        else:
            self.window.ui.dialogs.open('config.' + id, width=width, height=height)
            self.init(id)
            self.window.settings.active[id] = True

            # if no API key, focus on API key input
            if self.window.config.data['api_key'] is None or self.window.config.data['api_key'] == '':
                self.window.config_option['api_key'].setFocus()

        # update menu
        self.update()

    def toggle_editor(self, file=None):
        """
        Toggles editor

        :param file: JSON file to load
        """
        width = 500
        height = 600

        id = 'editor'
        current_file = self.window.dialog['config.editor'].file
        if id in self.window.settings.active and self.window.settings.active[id]:
            if current_file == file:
                self.window.ui.dialogs.close('config.' + id)
                self.window.settings.active[id] = False
            else:
                self.window.settings.load_editor(file)  # load file to editor
                self.window.dialog['config.editor'].file = file
        else:
            self.window.settings.load_editor(file)  # load file to editor
            self.window.ui.dialogs.open('config.' + id, width=width, height=height)
            self.window.settings.active[id] = True

        # update menu
        self.update()

    def close_window(self, id):
        """
        Closes window

        :param id: settings window id
        """
        if id in self.window.settings.active and self.window.settings.active[id]:
            self.window.ui.dialogs.close('config.' + id)
            self.window.settings.active[id] = False

    def close(self, id):
        """
        Closes menus

        :param id: settings window id
        """
        if id in self.window.menu:
            self.window.menu[id].setChecked(False)

        allowed_settings = ['settings']
        if id in allowed_settings and id in self.window.menu:
            self.window.menu[id].setChecked(False)

    def update(self):
        """Updates settings"""
        self.update_menu()

    def update_menu(self):
        """Updates menu"""
        for id in self.window.settings.ids:
            key = 'config.' + id
            if key in self.window.menu:
                if id in self.window.settings.active and self.window.settings.active[id]:
                    self.window.menu['config.' + id].setChecked(True)
                else:
                    self.window.menu['config.' + id].setChecked(False)

    def init(self, id):
        """
        Initializes settings

        :param id: settings window id
        """
        if id == 'settings':
            # slider + input
            self.apply('temperature', self.window.config.data['temperature'])
            self.apply('top_p', self.window.config.data['top_p'])
            self.apply('frequency_penalty', self.window.config.data['frequency_penalty'])
            self.apply('presence_penalty', self.window.config.data['presence_penalty'])
            self.apply('context_threshold', self.window.config.data['context_threshold'])
            self.apply('max_output_tokens', self.window.config.data['max_output_tokens'])
            self.apply('max_total_tokens', self.window.config.data['max_total_tokens'])
            self.apply('font_size', self.window.config.data['font_size'])
            self.apply('font_size.input', self.window.config.data['font_size.input'])
            self.apply('font_size.ctx', self.window.config.data['font_size.ctx'])

            # input
            self.change('api_key', self.window.config.data['api_key'])
            self.change('organization_key', self.window.config.data['organization_key'])
            self.change('img_resolution', self.window.config.data['img_resolution'])
            self.change('ctx.auto_summary.system', self.window.config.data['ctx.auto_summary.system'])
            self.change('ctx.auto_summary.prompt', self.window.config.data['ctx.auto_summary.prompt'])

            # checkbox
            self.toggle('use_context', self.window.config.data['use_context'])
            self.toggle('store_history', self.window.config.data['store_history'])
            self.toggle('store_history_time', self.window.config.data['store_history_time'])
            self.toggle('ctx.auto_summary', self.window.config.data['ctx.auto_summary'])

    def toggle(self, id, value, section=None):
        """
        Toggles checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.config_toggle(id, value, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.config_toggle(id, value)
            return

        # dialog: settings
        if id == 'store_history':
            self.window.config.data['store_history'] = value
        elif id == 'store_history_time':
            self.window.config.data['store_history_time'] = value
        elif id == 'use_context':
            self.window.config.data['use_context'] = value
        elif id == 'ctx.auto_summary':
            self.window.config.data['ctx.auto_summary'] = value

        self.window.config_option[id].box.setChecked(value)

    def change(self, id, value, section=None):
        """
        Changes input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.config_change(id, value, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.config_change(id, value)
            return

        # dialog: settings
        if id == 'temperature' \
                or id == 'top_p' \
                or id == 'frequency_penalty' \
                or id == 'presence_penalty':
            if value < 0:
                value = 0.0
            elif value > 2:
                value = 2.0
            self.window.config.data[id] = value
        elif id == 'context_threshold':
            if value < 0:
                value = 0.0
            elif value > 1000:
                value = 1000
            self.window.config.data[id] = round(int(value), 0)
        else:
            self.window.config.data[id] = value

        # update font size in real time
        if id.startswith('font_size'):
            self.update_font_size()

        txt = '{}'.format(value)
        self.window.config_option[id].setText(txt)

    def apply(self, id, value, type=None, section=None):
        """
        Applies slider + input value

        :param id: option id
        :param value: option value
        :param type: option type (slider, input, None)
        :param section: option section (settings, preset.editor, None)
        """
        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.config_slider(id, value, type, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.config_slider(id, value, type)
            return

        # dialog: settings
        integer_values = [
            'max_output_tokens',
            'max_total_tokens',
            'context_threshold',
            'img_variants',
            'font_size',
            'font_size.input',
            'font_size.ctx',
        ]
        params_values = [
            'temperature',
            'current_temperature',
            'top_p',
            'frequency_penalty',
            'presence_penalty',
        ]

        if id in integer_values:
            try:
                value = int(value)
            except:
                value = 0
                self.window.config_option[id].input.setText(str(value))

        multiplier = 1
        if id in params_values:
            multiplier = 100
            # fix / validate
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

        # img variants
        if id == 'img_variants':
            # fix / validate
            if type != 'slider':
                try:
                    value = int(value)
                except:
                    value = 1
                if value < 1:
                    value = 1
                elif value > 4:
                    value = 4
                self.window.config_option[id].input.setText(str(value))

        # font size
        elif id == 'font_size':
            # fix / validate
            if type != 'slider':
                try:
                    value = int(value)
                except:
                    value = 8
                if value < 8:
                    value = 8
                elif value > 20:
                    value = 20
                self.window.config_option[id].input.setText(str(value))

        slider_value = round(float(value) * multiplier, 0)
        input_value = value
        if type == 'slider':
            input_value = value / multiplier
            if id in integer_values:
                input_value = round(int(input_value), 0)

        # update current preset temperature if changed global temperature
        if id == 'current_temperature':
            preset = self.window.config.data['preset']  # current preset
            is_current = True
            if section == 'preset.editor':
                preset = self.window.config_option['preset.filename'].text()  # editing preset
                is_current = False
            self.window.controller.presets.update_field(id, input_value, preset, is_current)
            self.window.controller.presets.update_field('preset.temperature', input_value, True)
        else:
            if id not in integer_values:
                self.window.config.data[id] = float(input_value)
            else:
                self.window.config.data[id] = round(int(input_value), 0)

        # update from slider
        if type == 'slider':
            txt = '{}'.format(input_value)
            self.window.config_option[id].input.setText(txt)

        # update from input
        elif type == 'input' or type is None:
            if id in params_values:
                if slider_value < 1:
                    slider_value = 1
                elif slider_value > 200:
                    slider_value = 200
            elif id == 'max_output_tokens':
                if slider_value < 1:
                    slider_value = 1
                elif slider_value > 32000:
                    slider_value = 32000
            elif id == 'max_total_tokens':
                if slider_value < 1:
                    slider_value = 1
                elif slider_value > 256000:
                    slider_value = 256000
            self.window.config_option[id].slider.setValue(slider_value)

        # update from raw value
        if id.startswith('font_size'):
            self.update_font_size()  # update font size in real time

    def open_config_dir(self):
        """Opens user config directory"""
        if os.path.exists(self.window.config.path):
            show_in_file_manager(self.window.config.path)
        else:
            self.window.set_status('Config directory not exists: {}'.format(self.window.config.path))
