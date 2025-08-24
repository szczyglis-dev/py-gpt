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


class Theme:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window
        self._loaded = False

    def _on_toggle_tooltips(self, checked=False):
        self.window.controller.theme.toggle_option('layout.tooltips')

    def _open_settings(self, checked=False):
        self.window.controller.settings.open_section('layout')

    def setup(self):
        """Setup theme menu"""
        w = self.window
        m = w.ui.menu

        if self._loaded:
            act = m.get('theme.tooltips')
            if isinstance(act, QAction):
                act.setChecked(w.core.config.get('layout.tooltips'))
            return

        m['theme'] = {}
        m['theme_style'] = {}
        m['theme_syntax'] = {}
        m['theme.layout.density'] = {}
        m['menu.theme'] = QMenu(trans("menu.theme"), w)

        m['theme.style'] = QMenu(trans("menu.theme.style"), w)

        m['theme.dark'] = QMenu(trans("menu.theme.dark"), w)
        m['theme.light'] = QMenu(trans("menu.theme.light"), w)
        m['theme.syntax'] = QMenu(trans("menu.theme.syntax"), w)

        m['theme.density'] = QMenu(trans("menu.theme.density"), w)

        m['theme.tooltips'] = QAction(trans("menu.theme.tooltips"), w, checkable=True)
        m['theme.tooltips'].triggered.connect(self._on_toggle_tooltips)
        m['theme.tooltips'].setChecked(w.core.config.get('layout.tooltips'))

        m['theme.settings'] = QAction(QIcon(":/icons/settings_filled.svg"),
                                      trans("menu.theme.settings"), w)
        m['theme.settings'].setMenuRole(QAction.MenuRole.NoRole)
        m['theme.settings'].triggered.connect(self._open_settings)

        menu_theme = m['menu.theme']
        menu_theme.addMenu(m['theme.style'])
        menu_theme.addMenu(m['theme.dark'])
        menu_theme.addMenu(m['theme.light'])
        menu_theme.addMenu(m['theme.syntax'])
        menu_theme.addMenu(m['theme.density'])
        menu_theme.addAction(m['theme.tooltips'])
        menu_theme.addAction(m['theme.settings'])

        self._loaded = True