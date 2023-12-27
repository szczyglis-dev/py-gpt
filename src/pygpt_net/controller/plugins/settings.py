#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Plugin settings controller

        :param window: Window instance
        """
        self.window = window
        self.config_dialog = False
        self.config_initialized = False
        self.current_plugin = None

    def setup(self):
        """Set up plugin settings"""
        idx = None
        # restore previous selected or restored tab on dialog create
        if 'plugin.settings' in self.window.ui.tabs:
            idx = self.window.ui.tabs['plugin.settings'].currentIndex()
        self.window.plugin_settings.setup(idx)  # widget dialog Plugins

    def toggle_editor(self):
        """Toggle plugin settings dialog"""
        if self.config_dialog:
            self.close()
        else:
            self.open()

    def open(self):
        """Open plugin settings dialog"""
        if not self.config_initialized:
            self.setup()
            self.config_initialized = True
        if not self.config_dialog:
            self.init()
            self.window.ui.dialogs.open('plugin_settings', width=800, height=500)
            self.config_dialog = True

    def init(self):
        """Initialize plugin settings options"""
        selected_plugin = self.current_plugin

        # select first plugin on list if no plugin selected yet
        if selected_plugin is None:
            if len(self.window.core.plugins.plugins) > 0:
                selected_plugin = list(self.window.core.plugins.plugins.keys())[0]

        # assign plugin options to config dialog fields
        for id in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[id]
            options = plugin.setup()  # get plugin options
            self.current_plugin = id

            for key in options:
                option = options[key]
                option_id = 'plugin.' + id + '.' + key
                if option['type'] == 'text' or option['type'] == 'int' or option['type'] == 'float':
                    if 'slider' in option and option['slider'] \
                            and (option['type'] == 'int' or option['type'] == 'float'):
                        self.config_slider(option_id, option['value'])
                    else:
                        self.config_change(option_id, option['value'])
                elif option['type'] == 'textarea':
                    self.config_change(option_id, option['value'])
                elif option['type'] == 'bool':
                    self.config_toggle(option_id, option['value'])
                elif option['type'] == 'dict':
                    self.config_dict_update(option_id, option['value'])  # update model items

        self.current_plugin = selected_plugin  # restore selected plugin
        self.window.controller.layout.restore_plugin_settings()  # restore plugin settings layout

    def save(self):
        """Save plugin settings"""
        selected_plugin = self.current_plugin
        for id in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[id]
            options = plugin.setup()  # get plugin options

            # add plugin to config if not exists
            if id not in self.window.core.config.get('plugins'):
                self.window.core.config.data['plugins'][id] = {}

            self.current_plugin = id
            # update config with new values
            for key in options:
                option = options[key]
                value = None
                if option['type'] == 'int' or option['type'] == 'float':
                    if 'slider' in option and option['slider'] \
                            and (option['type'] == 'int' or option['type'] == 'float'):
                        value = self.window.ui.plugin_option[id][key].slider.value() / option['multiplier']
                    else:
                        if option['type'] == 'int':
                            try:
                                value = int(self.window.ui.plugin_option[id][key].text())
                            except ValueError:
                                value = 0
                        elif option['type'] == 'float':
                            try:
                                value = float(self.window.ui.plugin_option[id][key].text())
                            except ValueError:
                                value = 0.0
                elif option['type'] == 'text':
                    value = self.window.ui.plugin_option[id][key].text()
                elif option['type'] == 'textarea':
                    value = self.window.ui.plugin_option[id][key].toPlainText()
                elif option['type'] == 'bool':
                    value = self.window.ui.plugin_option[id][key].box.isChecked()
                elif option['type'] == 'dict':
                    value = self.window.ui.plugin_option[id][key].model.items
                self.window.core.plugins.plugins[id].options[key]['value'] = value
                self.window.core.config.data['plugins'][id][key] = value

            # update config if option not exists
            for key in list(self.window.core.config.data['plugins'].keys()):
                if key not in self.window.core.plugins.plugins:
                    self.window.core.config.data['plugins'].pop(key)

        # save config
        self.window.core.config.save()
        self.close()
        self.current_plugin = selected_plugin

    def close(self):
        """Close plugin settings dialog"""
        if self.config_dialog:
            self.window.ui.dialogs.close('plugin_settings')
            self.config_dialog = False

    def load_defaults_user(self, force=False):
        """
        Load plugin settings user defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm('plugin.settings.defaults.user', -1,
                                           trans('dialog.plugin.settings.defaults.user.confirm'))
            return

        # reload settings window
        self.init()
        # self.window.ui.dialogs.alert(trans('dialog.plugin.settings.defaults.user.result'))

    def load_defaults_app(self, force=False):
        """
        Load plugin settings app defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm('plugin.settings.defaults.app', -1,
                                           trans('dialog.plugin.settings.defaults.app.confirm'))
            return

        # restore default options
        self.window.core.plugins.restore_options(self.current_plugin)

        # reload settings window
        self.init()
        self.window.ui.dialogs.alert(trans('dialog.plugin.settings.defaults.app.result'))

    def config_toggle(self, id, value):
        """
        Toggle checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        """
        key = id.replace('plugin.' + self.current_plugin + '.', '')
        self.window.ui.plugin_option[self.current_plugin][key].box.setChecked(value)

    def config_dict_update(self, id, value):
        """
        Toggle dict items

        :param id: option id
        :param value: dict values
        """
        key = id.replace('plugin.' + self.current_plugin + '.', '')
        values = list(value)
        self.window.ui.plugin_option[self.current_plugin][key].items = values  # replace model data list
        self.window.ui.plugin_option[self.current_plugin][key].model.updateData(values)  # update model data

    def config_change(self, id, value):
        """
        Change input value

        :param id: input option id
        :param value: input option value
        """
        key = id.replace('plugin.' + self.current_plugin + '.', '')
        option = self.get_option(self.current_plugin, key)
        if 'type' in option and option['type'] == 'int':
            value = round(int(value), 0)
        elif 'type' in option and option['type'] == 'float':
            value = float(value)

        if 'type' in option and option['type'] == 'int' or option['type'] == 'float':
            if value is not None:
                if 'min' in option and option['min'] is not None and value < option['min']:
                    value = option['min']
                elif 'max' in option and option['max'] is not None and value > option['max']:
                    value = option['max']

        self.window.ui.plugin_option[self.current_plugin][key].setText('{}'.format(value))

    def config_slider(self, id, value, type=None):
        """
        Apply slider + input value

        :param id: option id
        :param value: option value
        :param type: option type (slider, input, None)
        """
        key = id.replace('plugin.' + self.current_plugin + '.', '')
        is_integer = False
        multiplier = 1

        option = self.get_option(self.current_plugin, key)
        if 'type' in option and option['type'] == 'int':
            is_integer = True
        if 'multiplier' in option:
            multiplier = option['multiplier']

        if type != 'slider':
            if is_integer:
                try:
                    value = round(int(value), 0)
                except:
                    value = 0
            else:
                try:
                    value = float(value)
                except:
                    value = 0.0

            if 'min' in option and value < option['min']:
                value = option['min']
            elif 'max' in option and value > option['max']:
                value = option['max']

            self.window.ui.plugin_option[self.current_plugin][key].input.setText(str(value))

        slider_value = round(float(value) * multiplier, 0)
        input_value = value
        if type == 'slider':
            input_value = value / multiplier
            if is_integer:
                input_value = round(int(input_value), 0)

        # update from slider
        if type == 'slider':
            txt = '{}'.format(input_value)
            self.window.ui.plugin_option[self.current_plugin][key].input.setText(txt)

        # update from input
        elif type == 'input':
            if 'min' in option and slider_value < option['min'] * multiplier:
                slider_value = option['min'] * multiplier
            elif 'max' in option and slider_value > option['max'] * multiplier:
                slider_value = option['max'] * multiplier
            self.window.ui.plugin_option[self.current_plugin][key].slider.setValue(slider_value)

        # update from raw value
        else:
            txt = '{}'.format(value)
            self.window.ui.plugin_option[self.current_plugin][key].input.setText(txt)
            self.window.ui.plugin_option[self.current_plugin][key].slider.setValue(slider_value)

    def get_option(self, id, key):
        """
        Get plugin option

        :param id: option id
        :param key: option key
        :return: option value
        :rtype: any
        """
        return self.window.core.plugins.plugins[id].options[key]
