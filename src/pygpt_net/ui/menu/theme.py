#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.24 02:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class Theme:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup theme menu"""
        self.window.ui.menu['theme'] = {}
        self.window.ui.menu['theme_syntax'] = {}
        self.window.ui.menu['theme.layout.density'] = {}
        self.window.ui.menu['menu.theme'] = QMenu(trans("menu.theme"), self.window)

        # color themes
        self.window.ui.menu['theme.dark'] = QMenu(trans("menu.theme.dark"), self.window)
        self.window.ui.menu['theme.light'] = QMenu(trans("menu.theme.light"), self.window)
        self.window.ui.menu['theme.syntax'] = QMenu(trans("menu.theme.syntax"), self.window)

        # layout density
        self.window.ui.menu['theme.density'] = QMenu(trans("menu.theme.density"), self.window)

        # blocks
        self.window.ui.menu['theme.blocks'] = QAction(trans("menu.theme.blocks"), self.window, checkable=True)
        self.window.ui.menu['theme.blocks'].triggered.connect(
            lambda: self.window.controller.theme.toggle_option('render.blocks'))
        self.window.ui.menu['theme.blocks'].setCheckable(True)
        self.window.ui.menu['theme.blocks'].setChecked(self.window.core.config.get('render.blocks'))

        # tooltips
        self.window.ui.menu['theme.tooltips'] = QAction(trans("menu.theme.tooltips"), self.window, checkable=True)
        self.window.ui.menu['theme.tooltips'].triggered.connect(
            lambda: self.window.controller.theme.toggle_option('layout.tooltips'))
        self.window.ui.menu['theme.tooltips'].setCheckable(True)
        self.window.ui.menu['theme.tooltips'].setChecked(self.window.core.config.get('layout.tooltips'))

        # settings
        self.window.ui.menu['theme.settings'] = QAction(QIcon(":/icons/settings_filled.svg"),
                                                        trans("menu.theme.settings"), self.window)
        self.window.ui.menu['theme.settings'].setMenuRole(QAction.MenuRole.NoRole)

        self.window.ui.menu['theme.settings'].triggered.connect(
            lambda: self.window.controller.settings.open_section('layout'))

        self.window.ui.menu['menu.theme'].addMenu(self.window.ui.menu['theme.dark'])
        self.window.ui.menu['menu.theme'].addMenu(self.window.ui.menu['theme.light'])
        self.window.ui.menu['menu.theme'].addMenu(self.window.ui.menu['theme.syntax'])
        self.window.ui.menu['menu.theme'].addMenu(self.window.ui.menu['theme.density'])
        self.window.ui.menu['menu.theme'].addAction(self.window.ui.menu['theme.blocks'])
        self.window.ui.menu['menu.theme'].addAction(self.window.ui.menu['theme.tooltips'])
        self.window.ui.menu['menu.theme'].addAction(self.window.ui.menu['theme.settings'])
