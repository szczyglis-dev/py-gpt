#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction

from ..dispatcher import Event
from ..utils import trans


class Plugins:
    def __init__(self, window=None):
        """
        Plugins controller

        :param window: Window instance
        """
        self.window = window
        self.config_dialog = False
        self.config_initialized = False
        self.current_plugin = None
        self.enabled = {}

    def setup(self):
        """
        Set up plugins
        """
        self.setup_menu()
        self.setup_ui()
        self.load_config()
        self.update()

    def setup_ui(self):
        """
        Set up plugins ui
        """
        for id in self.window.app.plugins.plugins:
            plugin = self.window.app.plugins.plugins[id]
            try:
                plugin.setup_ui()  # setup UI
            except AttributeError:
                pass
        # show/hide UI elements
        self.handle_enabled_types()

        # tmp dump locales
        # self.window.app.plugins.dump_plugin_locales()

    def setup_settings(self):
        """Set up plugins settings"""
        idx = None
        # restore previous selected or restored tab on dialog create
        if 'plugin.settings' in self.window.ui.tabs:
            idx = self.window.ui.tabs['plugin.settings'].currentIndex()
        self.window.plugin_settings.setup(idx)  # widget dialog Plugins

    def setup_menu(self):
        """Set up plugins menu"""
        for id in self.window.app.plugins.plugins:
            plugin = self.window.app.plugins.plugins[id]
            if id in self.window.ui.menu['plugins']:
                continue
            default_name = self.window.app.plugins.plugins[id].name
            trans_key = 'plugin.' + id
            name = trans(trans_key)
            if name == trans_key:
                name = default_name
            if plugin.use_locale:
                domain = 'plugin.{}'.format(id)
                name = trans('plugin.name', False, domain)
            self.window.ui.menu['plugins'][id] = QAction(name, self.window, checkable=True)
            self.window.ui.menu['plugins'][id].triggered.connect(
                lambda checked=None, id=id: self.window.controller.plugins.toggle(id))
            self.window.ui.menu['menu.plugins'].addAction(self.window.ui.menu['plugins'][id])

    def update(self):
        """Update plugins menu"""
        for id in self.window.ui.menu['plugins']:
            self.window.ui.menu['plugins'][id].setChecked(False)

        for id in self.enabled:
            if self.enabled[id]:
                self.window.ui.menu['plugins'][id].setChecked(True)

        self.handle_enabled_types()

    def destroy(self):
        """
        Destroy plugins workers
        """
        for id in self.window.app.plugins.plugins:
            plugin = self.window.app.plugins.plugins[id]
            try:
                plugin.destroy()  # destroy plugin workers
            except AttributeError:
                pass

    def toggle_settings(self):
        """Toggle plugins settings dialog"""
        if self.config_dialog:
            self.close_settings()
        else:
            self.open_settings()

    def open_settings(self):
        """Open plugins settings dialog"""
        if not self.config_initialized:
            self.setup_settings()
            self.config_initialized = True
        if not self.config_dialog:
            self.init_settings()
            self.window.ui.dialogs.open('plugin_settings', width=800, height=500)
            self.config_dialog = True

    def init_settings(self):
        """Initialize plugins settings options"""
        selected_plugin = self.current_plugin

        # select first plugin on list if no plugin selected yet
        if selected_plugin is None:
            if len(self.window.app.plugins.plugins) > 0:
                selected_plugin = list(self.window.app.plugins.plugins.keys())[0]

        # assign plugin options to config dialog fields
        for id in self.window.app.plugins.plugins:
            plugin = self.window.app.plugins.plugins[id]
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

    def save_settings(self):
        """Save plugins settings"""
        selected_plugin = self.current_plugin
        for id in self.window.app.plugins.plugins:
            plugin = self.window.app.plugins.plugins[id]
            options = plugin.setup()  # get plugin options

            # add plugin to config if not exists
            if id not in self.window.config.get('plugins'):
                self.window.config.data['plugins'][id] = {}

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
                self.window.app.plugins.plugins[id].options[key]['value'] = value
                self.window.config.data['plugins'][id][key] = value

            # update config if option not exists
            for key in list(self.window.config.data['plugins'].keys()):
                if key not in self.window.app.plugins.plugins:
                    self.window.config.data['plugins'].pop(key)

        # save config
        self.window.config.save()
        self.close_settings()
        self.current_plugin = selected_plugin

    def close_settings(self):
        """Close plugins settings dialog"""
        if self.config_dialog:
            self.window.ui.dialogs.close('plugin_settings')
            self.config_dialog = False

    def load_defaults_user(self, force=False):
        """
        Load plugins settings user defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm('plugin.settings.defaults.user', -1,
                                           trans('dialog.plugin.settings.defaults.user.confirm'))
            return

        # reload settings window
        self.init_settings()
        # self.window.ui.dialogs.alert(trans('dialog.plugin.settings.defaults.user.result'))

    def load_defaults_app(self, force=False):
        """
        Load plugins settings app defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm('plugin.settings.defaults.app', -1,
                                           trans('dialog.plugin.settings.defaults.app.confirm'))
            return

        # restore default options
        self.window.app.plugins.restore_options(self.current_plugin)

        # reload settings window
        self.init_settings()
        self.window.ui.dialogs.alert(trans('dialog.plugin.settings.defaults.app.result'))

    def register(self, plugin):
        """
        Register plugin

        :param plugin: Plugin
        """
        self.window.app.plugins.register(plugin)

    def unregister(self, id):
        """
        Unregister plugin

        :param id: Plugin id
        """
        if self.window.app.plugins.is_registered(id):
            self.window.app.plugins.plugins.pop(id)
            if id in self.enabled:
                self.enabled.pop(id)

    def enable(self, id):
        """
        Enable plugin

        :param id: plugin id
        """
        if self.window.app.plugins.is_registered(id):
            self.enabled[id] = True
            self.window.app.plugins.plugins[id].enabled = True

            # dispatch event
            event = Event('enable', {
                'value': id,
            })
            self.window.dispatch(event)

            self.window.config.data['plugins_enabled'][id] = True
            self.window.config.save()

            # update audio menu
            # TODO: by type loop
            if id == 'audio_azure' or id == 'audio_openai_tts' or id == 'audio_openai_whisper':
                self.window.controller.audio.update()

        self.update_info()
        self.update()

    def disable(self, id):
        """
        Disable plugin

        :param id: plugin id
        """
        if self.window.app.plugins.is_registered(id):
            self.enabled[id] = False
            self.window.app.plugins.plugins[id].enabled = False

            # dispatch event
            event = Event('disable', {
                'value': id,
            })
            self.window.dispatch(event)

            self.window.config.data['plugins_enabled'][id] = False
            self.window.config.save()

            # update audio menu
            if id == 'audio_azure' or id == 'audio_openai_tts' or id == 'audio_openai_whisper':
                self.window.controller.audio.update()

        self.update_info()
        self.update()

    def is_enabled(self, id):
        """
        Check if plugin is enabled

        :param id: plugin id
        :return: true if enabled
        :rtype: bool
        """
        if self.window.app.plugins.is_registered(id):
            if id in self.enabled:
                return self.enabled[id]
        return False

    def toggle(self, id):
        """
        Toggle plugin

        :param id: plugin id
        """
        if self.window.app.plugins.is_registered(id):
            if self.is_enabled(id):
                self.disable(id)
            else:
                self.enable(id)

        self.handle_enabled_types()

    def set_plugin_by_tab(self, idx):
        """
        Set current plugin by tab index

        :param idx: tab index
        """
        plugin_idx = 0
        for id in self.window.app.plugins.plugins:
            if self.window.app.plugins.plugins[id].options:
                if plugin_idx == idx:
                    self.current_plugin = id
                    break
                plugin_idx += 1
        current = self.window.ui.models['plugin.list'].index(idx, 0)
        self.window.ui.nodes['plugin.list'].setCurrentIndex(current)

    def get_plugin_tab_idx(self, plugin_id):
        """
        Get plugin tab index

        :param plugin_id: plugin id
        """
        plugin_idx = None
        i = 0
        for id in self.window.app.plugins.plugins:
            if id == plugin_id:
                plugin_idx = i
                break
            i += 1
        return plugin_idx

    def update_info(self):
        """Update plugins info"""
        enabled_list = []
        for id in self.window.app.plugins.plugins:
            if self.is_enabled(id):
                enabled_list.append(self.window.app.plugins.plugins[id].name)
        tooltip = " + ".join(enabled_list)

        count_str = ""
        c = 0
        if len(self.window.app.plugins.plugins) > 0:
            for id in self.window.app.plugins.plugins:
                if self.is_enabled(id):
                    c += 1

        if c > 0:
            count_str = "+ " + str(c) + " " + trans('chatbox.plugins')
        self.window.ui.nodes['chat.plugins'].setText(count_str)
        self.window.ui.nodes['chat.plugins'].setToolTip(tooltip)

    def load_config(self):
        """
        Load plugins config
        """
        for id in self.window.config.get('plugins_enabled'):
            if self.window.config.data['plugins_enabled'][id]:
                self.enable(id)

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
        :return: option value
        :rtype: any
        """
        return self.window.app.plugins.plugins[id].options[key]

    def is_type_enabled(self, type):
        """
        Check if plugin type is enabled

        :return: true if enabled
        :rtype: bool
        """
        enabled = False
        for id in self.window.app.plugins.plugins:
            if type in self.window.app.plugins.plugins[id].type and self.is_enabled(id):
                enabled = True
                break
        return enabled

    def handle_enabled_types(self):
        """
        Handle plugin type
        """
        for type in self.window.app.plugins.allowed_types:
            if type == 'audio.input':
                if self.is_type_enabled(type):
                    self.window.ui.plugin_addon['audio.input'].setVisible(True)
                else:
                    self.window.ui.plugin_addon['audio.input'].setVisible(False)
            elif type == 'audio.output':
                if self.is_type_enabled(type):
                    pass
                    # self.window.ui.plugin_addon['audio.output'].setVisible(True)
                else:
                    self.window.ui.plugin_addon['audio.output'].setVisible(False)

    def apply_cmds(self, ctx, cmds):
        """
        Apply commands

        :param ctx: ContextItem
        :param cmds: commands
        """
        commands = []
        for cmd in cmds:
            if 'cmd' in cmd:
                commands.append(cmd)

        if len(commands) == 0:
            return

        # dispatch 'cmd.execute' event
        event = Event('cmd.execute', {
            'commands': commands
        })
        event.ctx = ctx
        self.dispatch(event)

    def dispatch(self, event, all=False):
        """
        Dispatch event to plugins

        :param event: event to dispatch
        :param all: true if dispatch to all plugins (enabled or not)
        """
        for id in self.window.app.plugins.plugins:
            if self.is_enabled(id) or all:
                if event.stop:
                    break
                self.window.app.dispatcher.dispatch(id, event)
