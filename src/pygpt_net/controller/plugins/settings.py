#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.11 01:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event
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
        self.width = 800
        self.height = 500

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
            self.window.ui.dialogs.open('plugin_settings', width=self.width, height=self.height)
            self.config_dialog = True

    def open_plugin(self, id: str):
        """
        Open plugin settings dialog

        :param id: plugin id
        """
        self.current_plugin = id
        self.open()

    def init(self):
        """Initialize plugin settings options"""
        # select the first plugin on list if no plugin selected yet
        if self.current_plugin is None:
            if len(self.window.core.plugins.plugins) > 0:
                self.current_plugin = list(self.window.core.plugins.plugins.keys())[0]

        # assign plugins options to config dialog fields
        for id in self.window.core.plugins.plugins.keys():
            plugin = self.window.core.plugins.plugins[id]
            options = plugin.setup()  # get plugin options

            # load and apply options to config dialog
            self.window.controller.config.load_options('plugin.' + id, options)

        self.window.controller.layout.restore_plugin_settings()  # restore previous selected plugin tab

    def save(self):
        """Save plugin settings"""
        for id in self.window.core.plugins.plugins.keys():
            plugin = self.window.core.plugins.plugins[id]
            options = plugin.setup()  # get plugin options

            # add plugin to global config data if not exists
            if id not in self.window.core.config.get('plugins'):
                self.window.core.config.data['plugins'][id] = {}

            # update config with new values
            for key in options:
                value = self.window.controller.config.get_value(
                    parent_id='plugin.' + id, 
                    key=key, 
                    option=options[key],
                )
                self.window.core.plugins.plugins[id].options[key]['value'] = value
                self.window.core.config.data['plugins'][id][key] = value

            # remove key from config if plugin option not exists
            for key in list(self.window.core.config.data['plugins'].keys()):
                if key not in self.window.core.plugins.plugins:
                    self.window.core.config.data['plugins'].pop(key)

        # save preset
        self.window.controller.plugins.presets.save_current()

        # save config
        self.window.core.config.save()
        self.close()
        self.window.ui.status(trans('info.settings.saved'))

        # dispatch on update event
        event = Event(Event.PLUGIN_SETTINGS_CHANGED)
        self.window.core.dispatcher.dispatch(event)
        self.window.controller.ui.update_tokens()  # update tokens (if cmd syntax changed)

    def close(self):
        """Close plugin settings dialog"""
        if self.config_dialog:
            self.window.ui.dialogs.close('plugin_settings')
            self.config_dialog = False

    def load_defaults_user(self, force: bool = False):
        """
        Load plugin settings user defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='plugin.settings.defaults.user', 
                id=-1,
                msg=trans('dialog.plugin.settings.defaults.user.confirm'),
            )
            return

        # reload settings window
        self.init()
        # self.window.ui.dialogs.alert(trans('dialog.plugin.settings.defaults.user.result'))

    def load_defaults_app(self, force: bool = False):
        """
        Load plugin settings app defaults

        :param force: force load defaults
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='plugin.settings.defaults.app',
                id=-1,
                msg=trans('dialog.plugin.settings.defaults.app.confirm'),
            )
            return

        # restore default options
        self.window.core.plugins.restore_options(self.current_plugin)

        # reload settings window
        self.init()
        self.window.ui.dialogs.alert(trans('dialog.plugin.settings.defaults.app.result'))

    def get_option(self, id: str, key: str) -> any:
        """
        Get plugin option

        :param id: plugin id
        :param key: option key
        :return: option value
        """
        return self.window.core.plugins.plugins[id].options[key]
