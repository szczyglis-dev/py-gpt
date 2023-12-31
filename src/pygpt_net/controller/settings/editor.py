#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 21:00:00                  #
# ================================================== #

import copy

from pygpt_net.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Settings controller

        :param window: Window instance
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
        self.before_config = {}
        self.initialized = False

    def init(self, id: str):
        """
        Initialize settings

        :param id: settings window id
        """
        if id == 'settings':
            for option in self.options:
                if 'type' not in self.options[option]:
                    continue
                type = self.options[option]['type']

                # apply initial settings from current config
                if type == 'int' or type == 'float':
                    self.apply(option, self.window.core.config.get(option))
                elif type == 'bool':
                    self.toggle(option, self.window.core.config.get(option))
                elif type == 'text' or type == 'textarea':
                    self.change(option, self.window.core.config.get(option))

    def load(self):
        """Load settings options from config file"""
        self.load_config_options()

        # store copy of loaded config data
        self.before_config = copy.deepcopy(self.window.core.config.all())

    def load_config_options(self, initialize: bool = True):
        """
        Load settings options from config file

        :param initialize: True if marks settings as initialized
        """
        self.options = self.window.core.settings.get_options()
        if initialize:
            self.initialized = True

    def save(self, id: str = None):
        """
        Save settings

        :param id: settings id
        """
        if id == "settings":
            # save settings from input fields
            for option in self.options:
                if 'type' not in self.options[option]:
                    continue
                type = self.options[option]['type']
                if type == 'text':
                    self.window.core.config.set(option, self.window.ui.config_option[option].text())
                elif type == 'textarea':
                    self.window.core.config.set(option, self.window.ui.config_option[option].toPlainText())

        info = trans('info.settings.saved')
        self.window.core.config.save()
        self.window.ui.status(info)
        self.window.controller.ui.update_font_size()
        self.window.controller.ui.update()

        # update layout if needed
        if self.before_config['layout.density'] != self.window.core.config.get('layout.density'):
            self.window.controller.theme.reload()

        self.before_config = copy.deepcopy(self.window.core.config.all())
        self.window.controller.settings.close_window(id)

    def toggle(self, id: str, value: bool, section: str = None):
        """
        Toggle checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.editor.config_toggle(id, value, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.settings.config_toggle(id, value)
            return

        # dialog: settings, apply boolean values to config
        if id in self.options:
            if 'type' in self.options[id]:
                if self.options[id]['type'] == 'bool':
                    self.window.core.config.set(id, value)

                # call vision checkboxes events
                if id == "vision.capture.enabled":
                    self.window.ui.nodes['vision.capture.enable'].setChecked(value)
                if id == "vision.capture.auto":
                    self.window.ui.nodes['vision.capture.auto'].setChecked(value)

        # update checkbox
        if id in self.window.ui.config_option and value is not None:
            self.window.ui.config_option[id].box.setChecked(value)

    def change(self, id: str, value: any, section: str = None):
        """
        Change input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.editor.config_change(id, value, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.settings.config_change(id, value)
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
                    self.window.core.config.set(id, value)
                # integers
                elif option['type'] == 'int':
                    if value < option['min']:
                        value = option['min']
                    elif value > option['max']:
                        value = option['max']
                    self.window.core.config.set(id, round(int(value), 0))
                # text
                else:
                    self.window.core.config.set(id, value)

        # update font size in real time
        if id.startswith('font_size'):
            self.window.controller.ui.update_font_size()

        # update ctx limit in real time
        if id == 'ctx.records.limit':
            self.window.controller.ctx.update(True, False)

        txt = '{}'.format(value)
        self.window.ui.config_option[id].setText(txt)

    def apply(self, id: str, value: any, type: str = None, section: str = None):
        """
        Apply slider + input value

        :param id: option id
        :param value: option value
        :param type: option type (slider, input, None)
        :param section: option section (settings, preset.editor, None)
        """
        # dialog: preset
        if id.startswith('preset.'):
            self.window.controller.presets.editor.config_slider(id, value, type, section)
            return

        # dialog: plugin
        elif id.startswith('plugin.'):
            self.window.controller.plugins.settings.config_slider(id, value, type)
            return

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
                        self.window.ui.config_option[id].input.setText(str(value))
                elif option_type == 'float':
                    if 'multiplier' in option:
                        multiplier = option['multiplier']
                        if type != 'slider':
                            try:
                                value = float(value)
                            except:
                                value = option['min']
                                self.window.ui.config_option[id].input.setText(str(value))
                            if value < option['min']:
                                value = option['min']
                            elif value > option['max']:
                                value = option['max']
                            self.window.ui.config_option[id].input.setText(str(value))

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
                    self.window.ui.config_option[id].input.setText(str(value))
                # fix min max values
                if value < min:
                    value = min
                elif value > max:
                    value = max
                self.window.ui.config_option[id].input.setText(str(value))

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
            preset = self.window.core.config.get('preset')  # current preset
            is_current = True
            if section == 'preset.editor':
                preset = self.window.ui.config_option['preset.filename'].text()  # editing preset
                is_current = False
            self.window.controller.presets.editor.update_field(id, input_value, preset, is_current)
            self.window.controller.presets.editor.update_field('preset.temperature', input_value, True)
        else:
            if option_type != 'int' and id not in self.integer_values:
                # any float
                self.window.core.config.set(id, float(input_value))
            else:
                # any integer
                self.window.core.config.set(id, round(int(input_value), 0))

        # update from slider
        if type == 'slider':
            txt = '{}'.format(input_value)
            self.window.ui.config_option[id].input.setText(txt)

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
                self.window.ui.config_option[id].slider.setValue(slider_value)
        else:
            if id in self.options and self.options[id]['slider']:
                self.window.ui.config_option[id].slider.setValue(slider_value)

        # update from raw value
        if id.startswith('font_size'):
            self.window.controller.ui.update_font_size()  # update font size in real time

        # update ctx limit in real time
        if id == 'ctx.records.limit':
            self.window.controller.ctx.update(True, False)

        # update current
        if id == "temperature":
            self.apply('current_temperature', input_value, 'input', section)

    def toggle_collapsed(self, id: str, value: any, section: str):
        """
        Toggle collapsed state of section

        :param id: section
        :param value: value
        :param section: section
        """
        if id not in self.window.ui.groups:
            return

        self.window.ui.groups[id].collapse(value)

    def load_defaults_user(self, force: bool = False):
        """
        Load default user config

        :param force: force load
        """
        if not force:
            self.window.ui.dialogs.confirm('settings.defaults.user', -1, trans('settings.defaults.user.confirm'))
            return

        # load default user config
        self.window.core.settings.load_user_settings()

        # re-init settings
        self.window.controller.settings.init('settings')
        # self.window.ui.dialogs.alert(trans('dialog.settings.defaults.user.result'))

    def load_defaults_app(self, force: bool = False):
        """
        Load default app config

        :param force: force load
        """
        if not force:
            self.window.ui.dialogs.confirm('settings.defaults.app', -1, trans('settings.defaults.app.confirm'))
            return

        # load default user config
        self.window.core.settings.load_app_settings()

        # re-init settings
        self.window.controller.settings.init('settings')
        self.window.ui.dialogs.alert(trans('dialog.settings.defaults.app.result'))

    def delete_item(self, parent_object, id: str, force: bool = False):
        """
        Load delete item (from dict list) confirmation dialog or executes delete

        :param parent_object: parent object
        :param id: item id
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('settings.dict.delete', id, trans('settings.dict.delete.confirm'),
                                           parent_object)
            return

        # delete item
        if parent_object is not None:
            parent_object.delete_item_execute(id)

    def get_options(self) -> dict:
        """
        Return settings options dict

        :return: dict Options dict
        """
        return self.options
