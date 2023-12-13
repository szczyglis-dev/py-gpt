#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 13:00:00                  #
# ================================================== #
import json
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
        self.options = {}
        self.integer_values = {
            'img_variants': {
                'min': 1,
                'max': 4,
                'multiplier': 1,
            }
        }
        self.float_values = {
            'current_temperature': {
                'min': 0,
                'max': 2,
                'multiplier': 100,
            }
        }
        self.width = 500
        self.height = 600
        self.before_config = {}
        self.initialized = False

    def load(self):
        """Loads settings options from config file"""
        self.load_config_options()

        # store copy of loaded config data
        self.before_config = dict(self.window.config.data)

    def load_config_options(self, initialize=True):
        """
        Loads settings options from config file

        :param initialize: True if marks settings as initialized
        """
        path = os.path.join(self.window.config.get_root_path(), 'data', 'config', 'settings.json')
        if not os.path.isfile(path):
            return {}
        with open(path) as f:
            self.options = json.load(f)
            if initialize:
                self.initialized = True
            f.close()

    def save(self, id=None):
        """
        Saves settings

        :param id: settings id
        """
        if id == "settings":
            # save settings from input fields
            for option in self.options:
                if 'type' not in self.options[option]:
                    continue
                type = self.options[option]['type']
                if type == 'text':
                    self.window.config.data[option] = self.window.config_option[option].text()
                elif type == 'textarea':
                    self.window.config.data[option] = self.window.config_option[option].toPlainText()

        info = trans('info.settings.saved')
        self.window.config.save()
        self.window.set_status(info)
        self.close_window(id)
        self.update_font_size()
        self.window.controller.ui.update()

        # update layout if needed
        if self.before_config['layout.density'] != self.window.config.data['layout.density']:
            self.window.controller.theme.reload()

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
        if id in self.window.settings.active and self.window.settings.active[id]:
            self.close_window(id)
        else:
            self.window.ui.dialogs.open('config.' + id, width=self.width, height=self.height)
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
            self.window.ui.dialogs.open('config.' + id, width=self.width, height=self.height)
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
            for option in self.options:
                if 'type' not in self.options[option]:
                    continue
                type = self.options[option]['type']

                # apply initial settings from current config
                if type == 'int' or type == 'float':
                    self.apply(option, self.window.config.data[option])
                elif type == 'bool':
                    self.toggle(option, self.window.config.data[option])
                elif type == 'text' or type == 'textarea':
                    self.change(option, self.window.config.data[option])

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

        # dialog: settings, apply boolean values to config
        if id in self.options:
            if 'type' in self.options[id]:
                if self.options[id]['type'] == 'bool':
                    self.window.config.data[id] = value

                # call vision checkboxes events
                if id == "vision.capture.enabled":
                    self.window.data['vision.capture.enable'].setChecked(value)
                if id == "vision.capture.auto":
                    self.window.data['vision.capture.auto'].setChecked(value)

        # update checkbox
        self.window.config_option[id].box.setChecked(value)

    def change(self, id, value, section=None):
        """
        Changes input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        self.before_config = dict(self.window.config.data)

        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.config_change(id, value, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.config_change(id, value)
            return

        # update config value
        if id in self.options:
            if 'type' in self.options[id]:
                option = self.options[id]
                # floats
                if option['type'] == 'float':
                    if value < option['min']:
                        value = option['min']
                    elif value > option['max']:
                        value = option['max']
                    self.window.config.data[id] = value
                # integers
                elif option['type'] == 'int':
                    if value < option['min']:
                        value = option['min']
                    elif value > option['max']:
                        value = option['max']
                    self.window.config.data[id] = round(int(value), 0)
                # text
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
        self.before_config = dict(self.window.config.data)

        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.config_slider(id, value, type, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.config_slider(id, value, type)
            return

        orig_value = value

        # dialog: settings or global settings
        option_type = None
        multiplier = 1  # default multiplier

        # check if option is in settings
        if id in self.options:
            if 'type' in self.options[id]:
                option = self.options[id]
                option_type = option['type']
                # integers, nothing to do
                if option_type == 'int':
                    try:
                        value = int(value)
                    except:
                        value = 0
                        self.window.config_option[id].input.setText(str(value))
                elif option_type == 'float':
                    if 'multiplier' in option:
                        multiplier = option['multiplier']
                        if type != 'slider':
                            try:
                                value = float(value)
                            except:
                                value = option['min']
                                self.window.config_option[id].input.setText(str(value))
                            if value < option['min']:
                                value = option['min']
                            elif value > option['max']:
                                value = option['max']
                            self.window.config_option[id].input.setText(str(value))

        if id in self.float_values:
            multiplier = self.float_values[id]['multiplier']
        elif id in self.integer_values:
            multiplier = self.integer_values[id]['multiplier']

        if type != 'slider':
            if id in self.float_values or id in self.integer_values:
                min = None
                max = None
                if id in self.float_values:
                    min = self.float_values[id]['min']
                    max = self.float_values[id]['max']
                elif id in self.integer_values:
                    min = self.integer_values[id]['min']
                    max = self.integer_values[id]['max']
                try:
                    if id in self.float_values:
                        value = float(value)
                    elif id in self.integer_values:
                        value = int(value)
                except:
                    value = min
                    self.window.config_option[id].input.setText(str(value))
                # fix min max values
                if value < min:
                    value = min
                elif value > max:
                    value = max
                self.window.config_option[id].input.setText(str(value))

        # prepare slider value
        slider_value = round(float(value) * multiplier, 0)
        input_value = value

        # if from slider, update input value by multiplier division
        if type == 'slider':
            input_value = value / multiplier
            if option_type == 'int' or id in self.integer_values:
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
            if option_type != 'int' and id not in self.integer_values:
                # any float
                self.window.config.data[id] = float(input_value)
            else:
                # any integer
                self.window.config.data[id] = round(int(input_value), 0)

        # update from slider
        if type == 'slider':
            txt = '{}'.format(input_value)
            self.window.config_option[id].input.setText(txt)

        # update from input
        elif type == 'input':
            if option_type == 'float' or id in self.float_values:
                if id in self.float_values:
                    min = self.float_values[id]['min'] * self.float_values[id]['multiplier']
                    max = self.float_values[id]['max'] * self.float_values[id]['multiplier']
                else:
                    min = self.options[id]['min'] * self.options[id]['multiplier']
                    max = self.options[id]['max'] * self.options[id]['multiplier']
                if slider_value < min:
                    slider_value = min
                elif slider_value > max:
                    slider_value = max
            elif option_type == 'int':
                min = self.options[id]['min']
                max = self.options[id]['max']
                if slider_value < min:
                    slider_value = min
                elif slider_value > max:
                    slider_value = max
            if id in self.options and self.options[id]['slider']:
                self.window.config_option[id].slider.setValue(slider_value)
        else:
            if id in self.options and self.options[id]['slider']:
                self.window.config_option[id].slider.setValue(slider_value)

        # update from raw value
        if id.startswith('font_size'):
            self.update_font_size()  # update font size in real time

        # update current
        if id == "temperature":
            self.apply('current_temperature', input_value, 'input', section)

    def open_config_dir(self):
        """Opens user config directory"""
        if os.path.exists(self.window.config.path):
            show_in_file_manager(self.window.config.path)
        else:
            self.window.set_status('Config directory not exists: {}'.format(self.window.config.path))

    def load_defaults_user(self, force=False):
        """
        Loads default user config

        :param force: force load
        """
        if not force:
            self.window.ui.dialogs.confirm('settings.defaults.user', -1, trans('settings.defaults.user.confirm'))
            return

        # load default user config
        self.window.settings.load_user_settings()

    def load_defaults_app(self, force=False):
        """
        Loads default app config

        :param force: force load
        """
        if not force:
            self.window.ui.dialogs.confirm('settings.defaults.app', -1, trans('settings.defaults.app.confirm'))
            return

        # load default user config
        self.window.settings.load_app_settings()

    def get_options(self):
        """
        Returns settings options dict

        :return: dict Options dict
        """
        return self.options
