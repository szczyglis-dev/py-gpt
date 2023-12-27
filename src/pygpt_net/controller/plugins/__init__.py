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

from PySide6.QtGui import QAction

from .settings import Settings
from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Plugins:
    def __init__(self, window=None):
        """
        Plugins controller

        :param window: Window instance
        """
        self.window = window
        self.settings = Settings(window)
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
        for id in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[id]
            try:
                plugin.setup_ui()  # setup UI
            except AttributeError:
                pass
        # show/hide UI elements
        self.handle_enabled_types()

        # tmp dump locales
        # self.window.core.plugins.dump_plugin_locales()

    def setup_menu(self):
        """Set up plugins menu"""
        for id in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[id]
            if id in self.window.ui.menu['plugins']:
                continue
            default_name = self.window.core.plugins.plugins[id].name
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
        for id in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[id]
            try:
                plugin.destroy()  # destroy plugin workers
            except AttributeError:
                pass

    def unregister(self, id):
        """
        Unregister plugin

        :param id: plugin id
        """
        self.window.core.plugins.unregister(id)
        if id in self.enabled:
            self.enabled.pop(id)

    def enable(self, id):
        """
        Enable plugin

        :param id: plugin id
        """
        if self.window.core.plugins.is_registered(id):
            self.enabled[id] = True
            self.window.core.plugins.plugins[id].enabled = True

            # dispatch event
            event = Event('enable', {
                'value': id,
            })
            self.window.core.dispatcher.dispatch(event)

            self.window.core.config.data['plugins_enabled'][id] = True
            self.window.core.config.save()

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
        if self.window.core.plugins.is_registered(id):
            self.enabled[id] = False
            self.window.core.plugins.plugins[id].enabled = False

            # dispatch event
            event = Event('disable', {
                'value': id,
            })
            self.window.core.dispatcher.dispatch(event)

            self.window.core.config.data['plugins_enabled'][id] = False
            self.window.core.config.save()

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
        if self.window.core.plugins.is_registered(id):
            if id in self.enabled:
                return self.enabled[id]
        return False

    def toggle(self, id):
        """
        Toggle plugin

        :param id: plugin id
        """
        if self.window.core.plugins.is_registered(id):
            if self.is_enabled(id):
                self.disable(id)
            else:
                self.enable(id)

        self.handle_enabled_types()
        self.window.controller.ui.update_tokens()  # refresh tokens

    def set_by_tab(self, idx):
        """
        Set current plugin by tab index

        :param idx: tab index
        """
        plugin_idx = 0
        for id in self.window.core.plugins.plugins:
            if self.window.core.plugins.plugins[id].options:
                if plugin_idx == idx:
                    self.settings.current_plugin = id
                    break
                plugin_idx += 1
        current = self.window.ui.models['plugin.list'].index(idx, 0)
        self.window.ui.nodes['plugin.list'].setCurrentIndex(current)

    def get_tab_idx(self, plugin_id):
        """
        Get plugin tab index

        :param plugin_id: plugin id
        """
        plugin_idx = None
        i = 0
        for id in self.window.core.plugins.plugins:
            if id == plugin_id:
                plugin_idx = i
                break
            i += 1
        return plugin_idx

    def update_info(self):
        """Update plugins info"""
        enabled_list = []
        for id in self.window.core.plugins.plugins:
            if self.is_enabled(id):
                enabled_list.append(self.window.core.plugins.plugins[id].name)
        tooltip = " + ".join(enabled_list)

        count_str = ""
        c = 0
        if len(self.window.core.plugins.plugins) > 0:
            for id in self.window.core.plugins.plugins:
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
        for id in self.window.core.config.get('plugins_enabled'):
            if self.window.core.config.data['plugins_enabled'][id]:
                self.enable(id)

    def is_type_enabled(self, type):
        """
        Check if plugin type is enabled

        :return: true if enabled
        :rtype: bool
        """
        enabled = False
        for id in self.window.core.plugins.plugins:
            if type in self.window.core.plugins.plugins[id].type and self.is_enabled(id):
                enabled = True
                break
        return enabled

    def handle_enabled_types(self):
        """
        Handle plugin type
        """
        for type in self.window.core.plugins.allowed_types:
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

        :param ctx: CtxItem
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
        self.window.controller.command.dispatch(event)
