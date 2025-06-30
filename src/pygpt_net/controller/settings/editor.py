#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

import copy
from typing import Optional, Any, Dict

from pygpt_net.core.events import Event
from pygpt_net.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Settings editor controller

        :param window: Window instance
        """
        self.window = window
        self.options = {}
        self.sections = {}
        self.before_config = {}
        self.initialized = False

    def setup(self):
        """Set up plugin settings"""
        idx = None
        # restore previous selected or restored tab on dialog create
        if 'settings.section' in self.window.ui.tabs:
            idx = self.window.ui.tabs['settings.section'].currentIndex()
        self.window.settings.setup(idx)  # widget dialog Plugins

    def init(self, id: str):
        """
        Initialize settings

        :param id: settings window id
        """
        # add hooks for config update in real-time
        self.window.ui.add_hook("update.config.font_size", self.hook_update)
        self.window.ui.add_hook("update.config.font_size.input", self.hook_update)
        self.window.ui.add_hook("update.config.font_size.ctx", self.hook_update)
        self.window.ui.add_hook("update.config.font_size.toolbox", self.hook_update)
        self.window.ui.add_hook("update.config.zoom", self.hook_update)
        self.window.ui.add_hook("update.config.theme.markdown", self.hook_update)
        self.window.ui.add_hook("update.config.vision.capture.enabled", self.hook_update)
        self.window.ui.add_hook("update.config.vision.capture.auto", self.hook_update)
        self.window.ui.add_hook("update.config.ctx.records.limit", self.hook_update)
        self.window.ui.add_hook("update.config.ctx.convert_lists", self.hook_update)
        self.window.ui.add_hook("update.config.ctx.records.separators", self.hook_update)
        self.window.ui.add_hook("update.config.ctx.records.groups.separators", self.hook_update)
        self.window.ui.add_hook("update.config.ctx.records.pinned.separators", self.hook_update)
        self.window.ui.add_hook("update.config.ctx.records.folders.top", self.hook_update)
        self.window.ui.add_hook("update.config.layout.density", self.hook_update)
        self.window.ui.add_hook("update.config.layout.tooltips", self.hook_update)
        self.window.ui.add_hook("update.config.img_dialog_open", self.hook_update)
        self.window.ui.add_hook("update.config.access.voice_control", self.hook_update)
        self.window.ui.add_hook("update.config.debug", self.hook_update)
        self.window.ui.add_hook("update.config.notepad.num", self.hook_update)
        self.window.ui.add_hook("update.config.render.code_syntax", self.hook_update)
        self.window.ui.add_hook("update.config.theme.style", self.hook_update)
        # self.window.ui.add_hook("llama.idx.storage", self.hook_update)  # vector store update
        # self.window.ui.add_hook("update.config.llama.idx.list", self.hook_update)

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
        self.sections = self.window.core.settings.get_sections()
        if initialize:
            self.initialized = True

    def save(self, id: Optional[str] = None):
        """
        Save settings

        :param id: settings id
        """
        for key in self.options:
            if 'type' not in self.options[key]:
                continue
            value = self.window.controller.config.get_value(
                parent_id='config', 
                key=key, 
                option=self.options[key],
            )
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

        if not self.window.core.config.get('layout.tray'):
            self.window.core.config.set('layout.tray.minimize', False)

        self.window.core.config.save()
        self.window.update_status(trans('info.settings.saved'))
        self.window.controller.ui.update_font_size()
        self.window.controller.ui.update()

        self.window.core.idx.sync()
        self.window.controller.idx.update()

        # update layout if needed
        if self.config_changed('layout.density'):
            self.window.controller.theme.reload()

        # update dirs if needed
        if self.config_changed('upload.data_dir'):
            self.window.core.camera.install()
            self.window.core.image.install()
            self.window.core.filesystem.install()
            self.window.controller.files.update_explorer()

        # switch log level in runtime
        if self.config_changed('log.level'):
            self.window.controller.debug.set_log_level(self.window.core.config.get('log.level'))

        # reset dialog geometry if disabled
        if not self.window.core.config.get('layout.dialog.geometry.store'):
            self.window.core.config.set('layout.dialog.geometry', {})
            self.window.core.config.save()

        # update search result or ctx layout if needed
        if (self.config_changed('ctx.search_content') or
                self.config_changed('ctx.records.folders.top') or
                self.config_changed('ctx.records.groups.separators') or
                self.config_changed('ctx.records.pinned.separators') or
                self.config_changed('ctx.records.separators')):
            self.window.controller.ctx.update()

        # syntax highlighter style
        if self.config_changed('render.code_syntax'):
            value = self.window.core.config.get('render.code_syntax')
            self.window.controller.theme.toggle_syntax(value, update_menu=True)

        # style
        if self.config_changed('theme.style'):
            value = self.window.core.config.get('theme.style')
            self.window.controller.theme.toggle_style(value)

        # convert lists
        if self.config_changed('ctx.convert_lists'):
            self.window.controller.ctx.refresh()

        # access: voice control
        if self.config_changed('access.voice_control'):
            self.window.controller.access.voice.update()

        # reload loaders
        if self.config_changed('llama.hub.loaders.args') or self.config_changed('llama.hub.loaders.use_local'):
            self.window.core.idx.indexing.reload_loaders()
            self.window.tools.get("indexer").refresh()

        # update idx list
        if self.config_changed('llama.idx.list'):
            self.window.controller.idx.settings.update_idx_choices()
            self.window.tools.get("indexer").reload()

        # update idx storage
        if self.config_changed('llama.idx.storage'):
            self.window.tools.get("indexer").reload()

        # update file explorer if vector store provider changed
        self.window.controller.idx.indexer.update_explorer()

        # update chat output
        if self.config_changed('ctx.sources') or self.config_changed('ctx.audio'):
            self.window.controller.ctx.refresh()

        # update global shortcuts
        if self.config_changed('access.shortcuts'):
            self.window.setup_global_shortcuts()

        # update ENV
        self.window.core.config.setup_env()

        self.before_config = copy.deepcopy(self.window.core.config.all())
        self.window.controller.settings.close_window(id)

        # dispatch on update event
        event = Event(Event.SETTINGS_CHANGED)
        self.window.dispatch(event, all=True)

    def config_changed(self, key: str) -> bool:
        """
        Check if config changed

        :param key: config key
        :return: bool
        """
        if key in self.before_config and self.before_config[key] != self.window.core.config.get(key):
            return True
        return False

    def hook_update(
            self,
            key: str,
            value: Any,
            caller,
            *args,
            **kwargs
    ):
        """
        Hook: on settings update

        :param key: config key
        :param value: config value
        :param caller: caller name
        :param args: args
        :param kwargs: kwargs
        """
        if self.window.controller.reloading:
            return  # ignore hooks during reloading process

        if self.window.core.config.get(key) == value:
            return  # ignore if value is the same

        # update font size
        if key.startswith('font_size') and caller == "slider":
            self.window.core.config.set(key, value)
            self.window.controller.ui.update_font_size()

        elif key == "zoom" and caller == "slider":
            value = value / 100
            self.window.core.config.set(key, value)
            self.window.controller.ui.update_font_size()

        # update markdown
        elif key == "theme.markdown":
            self.window.core.config.set(key, value)
            self.window.controller.theme.markdown.update(force=True)

        elif key == "render.code_syntax":
            self.window.core.config.set(key, value)
            self.window.controller.theme.toggle_syntax(value, update_menu=True)

        elif key == "ctx.convert_lists":
            self.window.core.config.set(key, value)
            self.window.controller.ctx.refresh()

        elif key == "ctx.records.separators":
            self.window.core.config.set(key, value)
            self.window.controller.ctx.update()

        elif key == "ctx.records.groups.separators":
            self.window.core.config.set(key, value)
            self.window.controller.ctx.update()

        elif key == "ctx.records.pinned.separators":
            self.window.core.config.set(key, value)
            self.window.controller.ctx.update()

        elif key == "ctx.records.folders.top":
            self.window.core.config.set(key, value)
            self.window.controller.ctx.update()

        # update layout tooltips
        elif key == "layout.tooltips":
            self.window.core.config.set(key, value)
            self.window.controller.theme.common.toggle_tooltips()

        # access: voice control
        elif key == "access.voice_control":
            self.window.core.config.set(key, value)
            self.window.controller.access.voice.update()

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
        elif key == "layout.density" and caller == "slider":
            self.window.core.config.set(key, value)
            self.window.controller.theme.reload()
            self.window.controller.theme.menu.update_density()

        # toggle image dialog auto-open
        elif key == "img_dialog_open":
            self.window.core.config.set(key, value)
            self.window.ui.nodes['dialog.image.open.toggle'].setChecked(value)

        # debug: menu
        elif key == "debug":
            self.window.core.config.set(key, value)
            self.window.controller.debug.toggle_menu()

    def toggle_collapsed(
            self,
            id: str,
            value: Any,
            section: str
    ):
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
            self.window.ui.dialogs.confirm(
                type='settings.defaults.user', 
                id=-1,
                msg=trans('settings.defaults.user.confirm'),
            )
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
            self.window.ui.dialogs.confirm(
                type='settings.defaults.app', 
                id=-1,
                msg=trans('settings.defaults.app.confirm'),
            )
            return

        # load default user config
        self.window.core.settings.load_app_settings()

        # re-init settings
        self.init('settings')
        self.window.ui.dialogs.alert(trans('dialog.settings.defaults.app.result'))

    def load_editor_defaults_user(self, force: bool = False):
        """
        Load default user config

        :param force: force load
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='settings.editor.defaults.user',
                id=-1,
                msg=trans('settings.defaults.user.confirm'),
            )
            return
        self.window.core.settings.load_default_editor()

    def load_editor_defaults_app(self, force: bool = False):
        """
        Load default app config

        :param force: force load
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='settings.editor.defaults.app',
                id=-1,
                msg=trans('settings.defaults.app.confirm'),
            )
            return
        self.window.core.settings.load_default_editor_app()

    def get_sections(self) -> Dict[str, dict]:
        """
        Return settings sections dict

        :return: dict sections dict
        """
        return self.sections

    def get_options(
            self,
            section: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Return settings options dict

        :param section: section ID
        :return: dict options dict
        """
        if section is None:
            return self.options
        else:
            options = {}
            for key in self.options:
                if 'section' in self.options[key] \
                        and self.options[key]['section'] == section:
                    options[key] = self.options[key]
            return options

    def get_option(self, key: str) -> Dict[str, Any]:
        """
        Return settings option

        :param key: option key
        :return: dict option dict
        """
        if key not in self.options:
            return {}

        return self.options[key]
