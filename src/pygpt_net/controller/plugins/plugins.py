#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

from typing import List, Dict, Any, Optional

from PySide6.QtGui import QAction

from pygpt_net.core.types import (
    MODE_AGENT,
)
from pygpt_net.controller.plugins.presets import Presets
from pygpt_net.controller.plugins.settings import Settings
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Plugins:
    def __init__(self, window=None):
        """
        Plugins controller

        :param window: Window instance
        """
        self.window = window
        self.settings = Settings(window)
        self.presets = Presets(window)
        self.enabled = {}
        self._ids = None
        self._ids_with_update = None
        self._suspend_updates = 0

    def _begin_batch(self):
        """Begin batch updates"""
        self._suspend_updates += 1

    def _end_batch(self):
        """End batch updates"""
        if self._suspend_updates > 0:
            self._suspend_updates -= 1
        if self._suspend_updates == 0:
            self.update_info()
            self.update()

    def setup(self):
        """Set up plugins"""
        self.setup_menu()
        self.setup_ui()

        try:
            self.window.core.plugins.clean_presets()
        except Exception as e:
            self.window.core.debug.error(e)

        self.presets.preset_to_current()
        self.reconfigure(silent=True)

    def reconfigure(self, silent: bool = False):
        """
        Reconfigure plugins

        :param silent: silent mode
        """
        self.setup_config(silent=silent)
        self.update()
        self.presets.update_menu()

    def setup_ui(self):
        """Set up plugins UI"""
        pm = self.window.core.plugins
        for pid in pm.get_ids():
            plugin = pm.get(pid)
            fn = getattr(plugin, "setup_ui", None)
            if callable(fn):
                fn()

        self.handle_types()

    def setup_menu(self):
        """Set up plugins menu"""
        pm = self.window.core.plugins
        ui_menu = self.window.ui.menu
        menu_plugins = ui_menu['plugins']
        for pid in pm.get_ids(sort=True):
            if pid in menu_plugins:
                continue
            name = pm.get_name(pid)
            tooltip = pm.get_desc(pid)
            act = QAction(name, self.window, checkable=True)
            act.triggered.connect(lambda checked=None, id=pid: self.toggle(id))
            act.setToolTip(tooltip)
            menu_plugins[pid] = act
            ui_menu['menu.plugins'].addAction(act)

    def setup_config(self, silent: bool = False):
        """
        Enable plugins from config

        :param silent: silent mode
        """
        pm = self.window.core.plugins
        cfg = self.window.core.config
        cfg_enabled = cfg.get('plugins_enabled')
        self._begin_batch()
        try:
            for pid in pm.get_ids():
                if pid in cfg_enabled:
                    if cfg.data['plugins_enabled'][pid]:
                        self.enable(pid)
                    else:
                        self.disable(pid, silent=silent)
                else:
                    self.disable(pid, silent=silent)
        finally:
            self._end_batch()

    def update(self):
        """Update plugins menu"""
        menu_plugins = self.window.ui.menu['plugins']
        for pid, action in menu_plugins.items():
            action.setChecked(self.enabled.get(pid, False))

        self.handle_types()
        self.window.controller.ui.mode.update()
        self.window.controller.ui.vision.update()

    def enable(self, id: str):
        """
        Enable plugin

        :param id: plugin id
        """
        pm = self.window.core.plugins
        if not pm.is_registered(id):
            return
        if self.enabled.get(id, False):
            return

        self.enabled[id] = True
        pm.enable(id)

        event = Event(Event.ENABLE, {'value': id})
        self.window.dispatch(event)

        if self.has_type(id, 'audio.input') or self.has_type(id, 'audio.output'):
            self.window.controller.audio.update()

        if self._suspend_updates == 0:
            self.update_info()
            self.update()

    def disable(self, id: str, silent: bool = False):
        """
        Disable plugin

        :param id: plugin id
        :param silent: silent mode
        """
        pm = self.window.core.plugins
        if not pm.is_registered(id):
            return
        if not self.enabled.get(id, False):
            return

        self.enabled[id] = False
        pm.disable(id)

        if not silent:
            event = Event(Event.DISABLE, {'value': id})
            self.window.dispatch(event, all=True)
            if self.has_type(id, 'audio.input') or self.has_type(id, 'audio.output'):
                self.window.controller.audio.update()

        if self._suspend_updates == 0:
            self.update_info()
            self.update()

    def is_enabled(self, id: str) -> bool:
        """
        Check if plugin is enabled

        :param id: plugin id
        :return: True if enabled
        """
        return self.window.core.plugins.is_registered(id) and self.enabled.get(id, False)

    def toggle(self, id: str):
        """
        Toggle plugin

        :param id: plugin id
        """
        if self.window.core.plugins.is_registered(id):
            if self.is_enabled(id):
                self.disable(id)
            else:
                self.enable(id)

        self.window.controller.ui.update_tokens()
        self.window.controller.attachment.update()
        self.presets.save_current()

    def set_by_tab(self, idx: int):
        """
        Set current plugin by tab index

        :param idx: tab index
        """
        pm = self.window.core.plugins
        plugin_idx = 0
        for pid in pm.get_ids(sort=True):
            if pm.has_options(pid):
                if plugin_idx == idx:
                    self.settings.current_plugin = pid
                    break
                plugin_idx += 1
        current = self.window.ui.models['plugin.list'].index(idx, 0)
        self.window.ui.nodes['plugin.list'].setCurrentIndex(current)

    def get_tab_idx(self, plugin_id: str) -> Optional[int]:
        """
        Get plugin tab index

        :param plugin_id: plugin id
        :return: tab index or None if not found
        """
        pm = self.window.core.plugins
        for i, pid in enumerate(pm.get_ids(sort=True)):
            if pid == plugin_id:
                return i
        return None

    def unregister(self, id: str):
        """
        Unregister plugin

        :param id: plugin id
        """
        self.window.core.plugins.unregister(id)
        self.enabled.pop(id, None)

    def destroy(self):
        """Destroy plugins workers"""
        event = Event(Event.FORCE_STOP, {})
        self.window.dispatch(event)

        pm = self.window.core.plugins
        for pid in pm.get_ids():
            plugin = pm.get(pid)
            fn = getattr(pm, "destroy", None)
            if callable(fn):
                try:
                    pm.destroy(pid)
                except AttributeError:
                    pass

    def has_type(self, id: str, type: str):
        """
        Check if plugin has type

        :param id: plugin ID
        :param type: type to check
        :return: True if has type
        """
        pm = self.window.core.plugins
        if not pm.is_registered(id):
            return False
        return type in pm.get(id).type

    def is_type_enabled(self, type: str) -> bool:
        """
        Check if plugin type is enabled

        :param type: plugin type
        :return: True if enabled
        """
        pm = self.window.core.plugins
        return any((type in pm.get(pid).type) and self.is_enabled(pid) for pid in pm.get_ids())

    def handle_types(self):
        """Handle plugin type"""
        pm = self.window.core.plugins
        for t in pm.allowed_types:
            enabled = self.is_type_enabled(t)
            if t == 'audio.input':
                self.window.controller.audio.handle_audio_input(enabled)
            elif t == 'audio.output':
                self.window.controller.audio.handle_audio_output(enabled)
            elif t == 'schedule':
                if enabled:
                    self.window.ui.plugin_addon['schedule'].setVisible(True)
                    data = {'name': 'scheduled_tasks_count', 'value': 0}
                    event = Event(Event.PLUGIN_OPTION_GET, data)
                    self.window.dispatch(event)
                    num = event.data.get('value', 0)
                    self.window.ui.tray.update_schedule_tasks(num)
                else:
                    self.window.ui.plugin_addon['schedule'].setVisible(False)
                    self.window.ui.tray.hide_schedule_menu()

    def on_update(self):
        """Called on update"""
        pm = self.window.core.plugins
        for pid in pm.get_ids():
            if self.is_enabled(pid):
                fn = getattr(pm.get(pid), "on_update", None)
                if callable(fn):
                    fn()

    def on_post_update(self):
        """Called on post update"""
        pm = self.window.core.plugins
        if self._ids is None:
            self._ids = pm.get_ids()
        if self._ids_with_update is None:
            self._ids_with_update = [pid for pid in self._ids if hasattr(self.window.core.plugins.get(pid), "on_post_update")]
        if len(self._ids_with_update) == 0:
            return
        for pid in self._ids_with_update:
            if self.is_enabled(pid):
                fn = pm.get(pid).on_post_update
                if callable(fn):
                    fn()

    def update_info(self):
        """Update plugins info"""
        pm = self.window.core.plugins
        enabled_names = []
        c = 0
        for pid in pm.get_ids():
            if self.is_enabled(pid):
                c += 1
                enabled_names.append(pm.get(pid).name)

        tooltip = " + ".join(enabled_names)
        count_str = f"+ {c} {trans('chatbox.plugins')}" if c > 0 else ""
        self.window.ui.nodes['chat.plugins'].setText(count_str)
        self.window.ui.nodes['chat.plugins'].setToolTip(tooltip)

    def _apply_cmds_common(
            self,
            event_type: str,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]],
            all: bool = False,
            execute_only: bool = False
    ) -> Optional[List[Any]]:
        """
        Common method to apply commands

        This method is used for both inline and non-inline commands.

        :param event_type: name of the event type, either Event.CMD_EXECUTE or Event.CMD_INLINE
        :param ctx: CtxItem
        :param cmds: commands list, each command is a dictionary with keys like "cmd", "args", etc.
        :param all: True to apply all commands, False to apply only enabled commands
        :param execute_only: True to execute commands only, without any additional event
        :return: results: results of the command execution, if any (ctx.results)
        """
        commands = self.window.core.command.from_commands(cmds)
        if len(commands) == 0:
            return

        event = Event(event_type, {'commands': commands})
        mode = self.window.core.config.get('mode')
        self.log("Executing plugin commands..." if event_type == Event.CMD_EXECUTE else "Executing inline plugin commands...")
        change_status = True
        if mode == MODE_AGENT and len(cmds) == 1 and cmds[0].get("cmd") == "goal_update":
            change_status = False
        wait_str = trans('status.cmd.wait')
        if change_status:
            self.window.update_status(wait_str)

        ctx.results = []
        event.ctx = ctx
        if event_type == Event.CMD_EXECUTE:
            self.window.controller.command.dispatch(event, all=all, execute_only=execute_only)
        else:
            self.window.controller.command.dispatch(event)

        current = self.window.ui.get_status()
        if current == wait_str:
            self.window.update_status("")
        return ctx.results

    def apply_cmds(
            self,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]],
            all: bool = False,
            execute_only: bool = False
    ) -> Optional[List[Any]]:
        """
        Apply commands (CMD_EXECUTE event only)

        :param ctx: CtxItem
        :param cmds: commands list
        :param all: True to apply all commands, False to apply only enabled commands
        :param execute_only: True to execute commands only, without any additional event
        :return: results: results of the command execution, if any (ctx.results)
        """
        return self._apply_cmds_common(Event.CMD_EXECUTE, ctx, cmds, all=all, execute_only=execute_only)

    def apply_cmds_all(
            self,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]]
    ) -> Optional[List[Any]]:
        """
        Apply all commands (inline or not)

        :param ctx: CtxItem
        :param cmds: commands list
        :return: results: results of the command execution, if any (ctx.results)
        """
        if self.window.core.config.get("cmd"):
            return self.apply_cmds(ctx, cmds)
        else:
            return self.apply_cmds_inline(ctx, cmds)


    def apply_cmds_inline(
            self,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]]
    ) -> Optional[List[Any]]:
        """
        Apply inline commands

        :param ctx: CtxItem
        :param cmds: commands list
        :return: results: results of the command execution, if any (ctx.results)
        """
        return self._apply_cmds_common(Event.CMD_INLINE, ctx, cmds)

    def reload(self):
        """Reload plugins"""
        self.window.core.plugins.reload_all()
        self.setup()
        self.settings.init()
        self.update()

    def save_all(self):
        """Save plugin settings"""
        pm = self.window.core.plugins
        cfg_plugins = self.window.core.config.data['plugins']

        for pid, plugin in pm.plugins.items():
            plugin.setup()
            if pid not in cfg_plugins:
                cfg_plugins[pid] = {}
            dest = cfg_plugins[pid]
            for key, opt in plugin.options.items():
                dest[key] = opt['value']

        for key in list(cfg_plugins.keys()):
            if key not in pm.plugins:
                cfg_plugins.pop(key)

        self.window.controller.plugins.presets.save_current()
        self.window.core.config.save()

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)