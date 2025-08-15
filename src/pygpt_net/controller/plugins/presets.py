#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

from copy import deepcopy
from typing import Dict, Optional
from uuid import uuid4

from PySide6.QtGui import QAction

from pygpt_net.utils import trans


class Presets:
    def __init__(self, window=None):
        """
        Plugin presets controller

        :param window: Window instance
        """
        self.window = window
        self.config_initialized = False
        self.dialog = False
        self.width = 500
        self.height = 500
        self._sep_action = None

    def setup(self):
        """Set up plugin presets"""
        self.window.plugin_presets.setup()

    def new(self):
        """New preset dialog"""
        uuid = str(uuid4())
        self.window.ui.dialog['create'].id = 'plugin.preset'
        self.window.ui.dialog['create'].input.setText("")
        self.window.ui.dialog['create'].current = uuid
        self.window.ui.dialog['create'].show()

    def create(self, id: str, name: str):
        """
        Create preset

        :param id: preset ID
        :param name: preset name
        """
        if name.strip() == "":
            self.window.update_status("Preset name cannot be empty!")
            return
        presets = self.get_presets()
        presets[id] = {
            'name': name,
            'enabled': {},
            'config': {},
        }
        self.store(presets)
        self.current_to_preset(id)
        self.window.ui.dialog['create'].close()
        self.update_list()
        self.toggle(id)

    def open(self):
        """Open preset editor"""
        if not self.config_initialized:
            self.setup()
            self.config_initialized = True
        if not self.dialog:
            self.window.ui.dialogs.open(
                'preset.plugins.editor',
                width=self.width,
                height=self.height,
            )
            self.dialog = True

    def close(self):
        """Close plugin presets dialog"""
        if self.dialog:
            self.window.ui.dialogs.close('preset.plugins.editor')
            self.dialog = False

    def toggle_editor(self):
        """Toggle plugin presets dialog"""
        if self.dialog:
            self.close()
        else:
            self.open()

    def rename_by_idx(self, idx: int):
        """
        Rename preset by index

        :param idx: preset index
        """
        id = self.get_id_by_idx(idx)
        if id is None:
            return
        self.rename(id)

    def rename(self, id: str):
        """
        Rename preset

        :param id: preset ID
        """
        presets = self.get_presets()
        name = ""
        if id in presets:
            name = presets[id]['name']

        self.window.ui.dialog['rename'].id = 'plugin.preset'
        self.window.ui.dialog['rename'].input.setText(name)
        self.window.ui.dialog['rename'].current = id
        self.window.ui.dialog['rename'].show()

    def update_name(self, id: str, name: str):
        """
        Update preset name

        :param id: preset ID
        :param name: preset name
        """
        if name.strip() == "":
            self.window.update_status("Preset name cannot be empty!")
            return
        presets = self.get_presets()
        if id in presets:
            presets[id]['name'] = name
        self.store(presets)
        self.window.ui.dialog['rename'].close()
        self.update_list()
        self.update_menu()

    def delete(self, id: str):
        """
        Delete preset

        :param id: preset ID
        """
        presets = self.get_presets()
        if id in presets:
            del presets[id]
        self.store(presets)

        current = self.window.core.config.get('preset.plugins')
        if current == id:
            self.window.core.config.set('preset.plugins', '')
            self.window.core.config.save()

        self.update_list()
        self.update_menu()

    def store(self, presets: Dict[str, Dict]):
        """
        Store presets

        :param presets: presets dict
        """
        self.window.core.plugins.replace_presets(presets)
        self.window.core.plugins.save_presets()

    def get_id_by_idx(self, idx: int) -> Optional[str]:
        """
        Get preset id by index

        :param idx: preset index
        """
        presets = self.get_presets()
        if 0 <= idx < len(presets):
            return list(presets.keys())[idx]
        return None

    def select_by_idx(self, idx: int):
        """
        Select preset by index

        :param idx: preset index
        """
        id = self.get_id_by_idx(idx)
        if id is None:
            return
        self.toggle(id)

    def delete_by_idx(
            self,
            idx: int,
            force: bool = False
    ):
        """
        Delete preset by index

        :param idx: preset index
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='plugin.presets.delete',
                id=idx,
                msg=trans('confirm.preset.delete'),
            )
            return
        id = self.get_id_by_idx(idx)
        if id is None:
            return
        self.delete(id)

    def duplicate(self, id: str):
        """
        Duplicate preset

        :param id: preset ID
        """
        presets = self.get_presets()
        duplicate = deepcopy(presets[id])
        new_id = str(uuid4())
        duplicate['name'] = duplicate['name'] + " - copy"
        presets[new_id] = duplicate
        self.store(presets)
        self.update_list()
        self.update_menu()

    def duplicate_by_idx(self, idx: int):
        """
        Duplicate preset by index

        :param idx: preset index
        """
        id = self.get_id_by_idx(idx)
        if id is None:
            return
        self.duplicate(id)

    def reset(self, id: str):
        """
        Reset preset

        :param id: preset ID
        """
        presets = self.get_presets()
        if id in presets:
            presets[id]['enabled'] = {}
            presets[id]['config'] = {}
            self.store(presets)
            if self.get_current_id() == id:
                self.toggle(id)
            self.window.update_status("Preset cleared: " + presets[id]['name'])

    def reset_by_idx(
            self,
            idx: int,
            force: bool = False
    ):
        """
        Reset preset by index

        :param idx: preset index
        :param force: force reset
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='plugin.presets.reset',
                id=idx,
                msg=trans('confirm.preset.clear'),
            )
            return
        id = self.get_id_by_idx(idx)
        if id is None:
            return
        self.reset(id)

    def get_preset(self, id: str) -> Dict:
        """
        Get preset by id

        :param id: preset ID
        :return: preset dict
        """
        presets = self.get_presets()
        if id in presets:
            return presets[id]

    def get_presets(self) -> Dict[str, Dict]:
        """
        Get presets dict

        :return: presets dict
        """
        presets = self.window.core.plugins.get_presets()
        if not isinstance(presets, dict) or not presets:
            return {}
        try:
            return dict(sorted(presets.items(), key=lambda item: item[1].get('name', '')))
        except Exception as e:
            self.window.core.debug.log("Error while sorting presets")
            self.window.core.debug.error(e)
            return presets

    def update_list(self):
        """Reload items"""
        items = self.get_presets()
        self.window.plugin_presets.update_list("preset.plugins.list", items)

    def update_menu(self):
        """Update presets menu"""
        presets = self.get_presets()
        menu_store = self.window.ui.menu
        menu = menu_store['menu.plugins.presets']

        old_actions = list(menu_store['plugins_presets'].values())
        for act in old_actions:
            menu.removeAction(act)
            act.deleteLater()
        menu_store['plugins_presets'].clear()

        if self._sep_action is not None:
            menu.removeAction(self._sep_action)
            self._sep_action.deleteLater()
            self._sep_action = None

        if len(presets) > 0:
            self._sep_action = menu.addSeparator()

        for id, preset in presets.items():
            action = QAction(preset['name'], menu, checkable=True)
            action.triggered.connect(lambda checked=False, id=id: self.window.controller.plugins.presets.toggle(id))
            action.setMenuRole(QAction.MenuRole.NoRole)
            menu.addAction(action)
            menu_store['plugins_presets'][id] = action

        self.update()

    def update(self):
        """Update presets menu"""
        presets_menu = self.window.ui.menu['plugins_presets']
        for preset in presets_menu:
            presets_menu[preset].setChecked(False)

        preset = self.window.core.config.get('preset.plugins')
        if preset in presets_menu:
            presets_menu[preset].setChecked(True)

    def toggle(self, id: str):
        """
        Toggle preset

        :param id: preset ID to toggle
        """
        self.window.core.config.set('preset.plugins', id)
        self.window.core.config.save()
        self.update()

        self.preset_to_current()
        self.window.controller.plugins.reconfigure()

        preset = self.get_preset(id)
        if preset:
            self.window.update_status("Preset loaded: " + preset['name'])

    def get_current_id(self) -> str:
        """
        Get current preset id

        :return: preset id
        """
        return self.window.core.config.get('preset.plugins')

    def save_current(self):
        """Save current settings as preset"""
        id = self.window.core.config.get('preset.plugins')
        if id:
            preset = self.get_preset(id)
            if preset:
                self.current_to_preset(id)

    def preset_to_current(self):
        """Load settings from preset"""
        id = self.window.core.config.get('preset.plugins')
        if id:
            preset = self.get_preset(id)
            if preset:
                self.window.core.config.set('plugins_enabled', deepcopy(preset['enabled']))
                self.window.core.config.set('plugins', deepcopy(preset['config']))
                self.window.core.config.save()
                self.window.core.plugins.apply_all_options()
                if self.window.controller.plugins.settings.config_dialog:
                    self.window.controller.plugins.settings.init()

    def current_to_preset(self, preset_id: str):
        """
        Store current config to preset

        :param preset_id: preset id
        """
        presets = self.get_presets()
        if preset_id in presets:
            presets[preset_id]['enabled'] = deepcopy(self.window.core.config.get('plugins_enabled'))
            presets[preset_id]['config'] = deepcopy(self.window.core.config.get('plugins'))
            self.store(presets)
        self.update_list()
        self.update_menu()