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
        self.before_config = {}
        self.initialized = False

    def init(self, id: str):
        """
        Initialize settings

        :param id: settings window id
        """
        # add hooks for config update in real-time
        self.window.config_bag.add_hook("update.config.font_size", self.hook_update)
        self.window.config_bag.add_hook("update.config.font_size.input", self.hook_update)
        self.window.config_bag.add_hook("update.config.font_size.ctx", self.hook_update)
        self.window.config_bag.add_hook("update.config.font_size.toolbox", self.hook_update)
        self.window.config_bag.add_hook("update.config.theme.markdown", self.hook_update)
        self.window.config_bag.add_hook("update.config.render.plain", self.hook_update)
        self.window.config_bag.add_hook("update.config.vision.capture.enabled", self.hook_update)
        self.window.config_bag.add_hook("update.config.vision.capture.auto", self.hook_update)
        self.window.config_bag.add_hook("update.config.ctx.records.limit", self.hook_update)
        self.window.config_bag.add_hook("update.config.layout.density", self.hook_update)

        if id == 'settings':
            options = {}
            for key in self.options:
                if 'type' not in self.options[key]:
                    continue
                options[key] = self.options[key]
                options[key]['value'] = self.window.core.config.get(key)  # append current config value
            self.window.controller.config.load_options('config', options)

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
        for key in self.options:
            if 'type' not in self.options[key]:
                continue
            value = self.window.controller.config.get_value('config', key, self.options[key])
            self.window.core.config.set(key, value)

            # update preset temperature
            if key == "temperature":
                preset_id = self.window.core.config.get('preset')
                if preset_id is not None and preset_id != "":
                    if preset_id in self.window.core.presets.items:
                        preset = self.window.core.presets.items[preset_id]
                        preset.temperature = value
                        self.window.core.presets.save(preset_id)
                        self.window.controller.mode.update_temperature(value)  # update current temperature

        self.window.core.config.save()
        self.window.ui.status(trans('info.settings.saved'))
        self.window.controller.ui.update_font_size()
        self.window.controller.ui.update()

        # update layout if needed
        if self.before_config['layout.density'] != self.window.core.config.get('layout.density'):
            self.window.controller.theme.reload()

        self.before_config = copy.deepcopy(self.window.core.config.all())
        self.window.controller.settings.close_window(id)

    def hook_update(self, key, value, caller, *args, **kwargs):
        """
        Hook: on settings update
        """
        if self.window.core.config.get(key) == value:
            return

        # update font size
        if key.startswith('font_size') and caller == "slider":
            self.window.core.config.set(key, value)
            self.window.controller.ui.update_font_size()

        # update markdown
        elif key == "theme.markdown":
            self.window.core.config.set(key, value)
            self.window.controller.theme.update_markdown(force=True)

        # update raw output
        elif key == "render.plain":
            self.window.core.config.set(key, value)
            if not value:
                self.window.controller.ctx.refresh()
                self.window.controller.theme.update_markdown(force=True)
                self.window.ui.nodes['output.raw'].setChecked(False)
            else:
                self.window.controller.theme.clear_markdown()
                self.window.ui.nodes['output.raw'].setChecked(True)

        # call vision checkboxes events
        elif key == "vision.capture.enabled":
            self.window.core.config.set(key, value)
            self.window.ui.nodes['vision.capture.enable'].setChecked(value)

        elif key == "vision.capture.auto":
            self.window.core.config.set(key, value)
            self.window.ui.nodes['vision.capture.auto'].setChecked(value)

        # update ctx limit
        elif key.startswith('ctx.records.limit') and caller == "slider":
            self.window.core.config.set(key, value)
            self.window.controller.ctx.update(True, False)

        # update layout density
        elif key == 'layout.density' and caller == "slider":
            self.window.core.config.set(key, value)
            self.window.controller.theme.reload()

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
        self.init('settings')
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
        self.init('settings')
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
