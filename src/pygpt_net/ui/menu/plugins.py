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

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.utils import trans


class Plugins:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup plugins menu"""
        w = self.window
        ui_menu = w.ui.menu
        plugins_ctrl = w.controller.plugins

        txt_plugins = trans("menu.plugins")
        txt_settings = trans("menu.plugins.settings")
        txt_presets = trans("menu.plugins.presets")
        txt_presets_new = trans("menu.plugins.presets.new")
        txt_presets_edit = trans("menu.plugins.presets.edit")

        settings_action = ui_menu.get('plugins.settings')
        if settings_action is None:
            settings_action = QAction(QIcon(":/icons/settings_filled.svg"), txt_settings, w)
            settings_action.setMenuRole(QAction.MenuRole.NoRole)
            settings_action.triggered.connect(lambda _=False, f=plugins_ctrl.settings.toggle_editor: f())
            ui_menu['plugins.settings'] = settings_action
        else:
            settings_action.setText(txt_settings)
            settings_action.setIcon(QIcon(":/icons/settings_filled.svg"))
            settings_action.setMenuRole(QAction.MenuRole.NoRole)

        ui_menu.setdefault('plugins_presets', {})
        presets_menu = ui_menu.get('menu.plugins.presets')
        if presets_menu is None:
            presets_menu = QMenu(txt_presets, w)
            ui_menu['menu.plugins.presets'] = presets_menu
        else:
            presets_menu.setTitle(txt_presets)

        new_action = ui_menu.get('plugins.presets.new')
        if new_action is None:
            new_action = QAction(QIcon(":/icons/add.svg"), txt_presets_new, w, checkable=False)
            new_action.triggered.connect(lambda _=False, f=plugins_ctrl.presets.new: f())
            new_action.setMenuRole(QAction.MenuRole.NoRole)
            ui_menu['plugins.presets.new'] = new_action
        else:
            new_action.setText(txt_presets_new)
            new_action.setIcon(QIcon(":/icons/add.svg"))
            new_action.setMenuRole(QAction.MenuRole.NoRole)
        if new_action not in presets_menu.actions():
            presets_menu.addAction(new_action)

        edit_action = ui_menu.get('plugins.presets.edit')
        if edit_action is None:
            edit_action = QAction(QIcon(":/icons/edit.svg"), txt_presets_edit, w, checkable=False)
            edit_action.triggered.connect(lambda _=False, f=plugins_ctrl.presets.toggle_editor: f())
            edit_action.setMenuRole(QAction.MenuRole.NoRole)
            ui_menu['plugins.presets.edit'] = edit_action
        else:
            edit_action.setText(txt_presets_edit)
            edit_action.setIcon(QIcon(":/icons/edit.svg"))
            edit_action.setMenuRole(QAction.MenuRole.NoRole)
        if edit_action not in presets_menu.actions():
            presets_menu.addAction(edit_action)

        ui_menu.setdefault('plugins', {})
        plugins_menu = ui_menu.get('menu.plugins')
        if plugins_menu is None:
            plugins_menu = w.menuBar().addMenu(txt_plugins)
            ui_menu['menu.plugins'] = plugins_menu
        else:
            plugins_menu.setTitle(txt_plugins)

        if presets_menu.menuAction() not in plugins_menu.actions():
            plugins_menu.addMenu(presets_menu)
        if settings_action not in plugins_menu.actions():
            plugins_menu.addAction(settings_action)
        plugins_menu.setToolTipsVisible(True)