#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import copy
from typing import Dict
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

    def setup(self):
        """Set up plugin presets"""
        self.window.plugin_presets.setup()  # widget dialog

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
        self.update_menu()

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

        # set dialog and show
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

        # remove current preset if exists
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

    def get_id_by_idx(self, idx: int) -> str:
        """
        Get preset id by index

        :param idx: preset index
        """
        presets = self.get_presets()
        if len(presets) > idx:
            return list(presets.keys())[idx]

    def select_by_idx(self, idx: int):
        """
        Select preset by index

        :param idx: preset index
        """
        id = self.get_id_by_idx(idx)
        self.toggle(id)
        self.update_menu()

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
        self.delete(id)

    def duplicate(self, id: str):
        """
        Duplicate preset

        :param id: preset ID
        """
        presets = self.get_presets()
        duplicate = copy.deepcopy(presets[id])
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
        if not isinstance(presets, dict):
            presets = {}
            return presets

        # sort by name
        try:
            return dict(sorted(presets.items(), key=lambda item: item[1]['name']))
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

        # clear presets
        for id in self.window.ui.menu['plugins_presets']:
            self.window.ui.menu['menu.plugins.presets'].removeAction(self.window.ui.menu['plugins_presets'][id])

        # remove separator if exists
        if len(self.window.ui.menu['menu.plugins.presets'].actions()) > 2:
            self.window.ui.menu['menu.plugins.presets'].actions()[-1].deleteLater()

        # add separator
        if len(presets) > 0:
            self.window.ui.menu['menu.plugins.presets'].addSeparator()

        # add presets
        for id in presets:
            preset = presets[id]
            self.window.ui.menu['plugins_presets'][id] = QAction(preset['name'], self.window, checkable=True)
            self.window.ui.menu['plugins_presets'][id].triggered.connect(
                lambda checked=None,
                       id=id: self.window.controller.plugins.presets.toggle(id))
            self.window.ui.menu['plugins_presets'][id].setMenuRole(QAction.MenuRole.NoRole)
            self.window.ui.menu['menu.plugins.presets'].addAction(self.window.ui.menu['plugins_presets'][id])

        # update current preset
        self.update()

    def update(self):
        """Update presets menu"""
        # clear
        for preset in self.window.ui.menu['plugins_presets']:
            self.window.ui.menu['plugins_presets'][preset].setChecked(False)

        # set checked current preset
        preset = self.window.core.config.get('preset.plugins')
        if preset in self.window.ui.menu['plugins_presets']:
            self.window.ui.menu['plugins_presets'][preset].setChecked(True)

    def toggle(self, id: str):
        """
        Toggle preset

        :param id: preset ID to toggle
        """
        self.window.core.config.set('preset.plugins', id)
        self.window.core.config.save()
        self.update_menu()

        # load preset to current settings
        self.preset_to_current()
        self.window.controller.plugins.reconfigure()  # reconfigure plugins

        # update status
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
                self.window.core.config.set('plugins_enabled', copy.deepcopy(preset['enabled']))
                self.window.core.config.set('plugins', copy.deepcopy(preset['config']))
                self.window.core.config.save()
                self.window.core.plugins.apply_all_options()  # apply restored config

                # if settings dialog opened then reinitialize
                if self.window.controller.plugins.settings.config_dialog:
                    self.window.controller.plugins.settings.init()

    def current_to_preset(self, preset_id: str):
        """
        Store current config to preset

        :param preset_id: preset id
        """
        presets = self.get_presets()
        if preset_id in presets:
            presets[preset_id]['enabled'] = copy.deepcopy(self.window.core.config.get('plugins_enabled'))
            presets[preset_id]['config'] = copy.deepcopy(self.window.core.config.get('plugins'))
            self.store(presets)
        self.update_list()
        self.update_menu()