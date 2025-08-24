#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from typing import Any

from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import Event, KernelEvent
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
        if 'plugin.settings' in self.window.ui.tabs:
            idx = self.window.ui.tabs['plugin.settings'].currentIndex()
        self.window.plugin_settings.setup(idx)

    def toggle_editor(self):
        """Toggle plugin settings dialog"""
        if self.config_dialog:
            self.close()
        else:
            self.open()

    def open(self):
        """Open plugin settings dialog"""
        if not self.config_initialized:
            self.window.dispatch(KernelEvent(KernelEvent.STATUS, {
                'status': trans("status.loading")
            }))
            QApplication.processEvents()
            self.setup()
            self.config_initialized = True
        if self.config_dialog:
            return
        self.init()
        self.window.ui.dialogs.open(
            'plugin_settings',
            width=self.width,
            height=self.height
        )
        self.window.dispatch(KernelEvent(KernelEvent.STATUS, {
            'status': ""
        }))
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
        plugins = self.window.core.plugins.plugins
        if self.current_plugin is None and plugins:
            self.current_plugin = next(iter(plugins))
        cfg = self.window.controller.config
        for pid, plugin in plugins.items():
            options = plugin.setup()
            cfg.load_options(f'plugin.{pid}', options)
        self.window.controller.layout.restore_plugin_settings()

    def refresh_option(self, id: str, key: str):
        """
        Refresh plugin option

        :param id: plugin id
        :param key: option key
        """
        plugins = self.window.core.plugins.plugins
        plugin = plugins.get(id)
        if not plugin:
            return
        options = plugin.options
        if key not in options:
            return
        option = options[key]
        self.window.controller.config.placeholder.apply(option)
        items = option.get("keys", {})
        self.window.controller.config.update_list(
            option=option,
            parent_id=f'plugin.{id}',
            key=key,
            items=items,
        )

    def save(self):
        """Save plugin settings"""
        window = self.window
        plugins = window.core.plugins.plugins
        controller_cfg = window.controller.config
        config_data = window.core.config.data
        plugins_cfg = config_data.setdefault('plugins', {})

        for pid, plugin in plugins.items():
            options = plugin.setup()
            dst = plugins_cfg.setdefault(pid, {})
            for key, opt in options.items():
                value = controller_cfg.get_value(
                    parent_id=f'plugin.{pid}',
                    key=key,
                    option=opt,
                )
                plugin.options[key]['value'] = value
                dst[key] = value

        stale = set(plugins_cfg.keys()) - set(plugins.keys())
        for pid in stale:
            plugins_cfg.pop(pid, None)

        window.controller.plugins.presets.save_current()
        window.core.config.save()
        self.close()

        window.update_status(trans('info.settings.saved'))
        window.dispatch(Event(Event.PLUGIN_SETTINGS_CHANGED))
        window.controller.ui.update_tokens()

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
        self.init()

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
        self.window.core.plugins.restore_options(self.current_plugin)
        self.init()
        self.window.ui.dialogs.alert(trans('dialog.plugin.settings.defaults.app.result'))

    def get_option(self, id: str, key: str) -> Any:
        """
        Get plugin option

        :param id: plugin id
        :param key: option key
        :return: option value
        """
        return self.window.core.plugins.plugins[id].options[key]