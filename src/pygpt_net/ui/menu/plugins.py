#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.16 16:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class Plugins:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup plugins menu"""
        self.window.ui.menu['plugins.settings'] = QAction(QIcon(":/icons/settings_filled.svg"),
                                                          trans("menu.plugins.settings"), self.window)
        self.window.ui.menu['plugins.settings'].setMenuRole(QAction.MenuRole.NoRole)

        self.window.ui.menu['plugins.settings'].triggered.connect(
            lambda: self.window.controller.plugins.settings.toggle_editor())

        self.window.ui.menu['plugins'] = {}
        self.window.ui.menu['menu.plugins'] = self.window.menuBar().addMenu(trans("menu.plugins"))
        self.window.ui.menu['menu.plugins'].addAction(self.window.ui.menu['plugins.settings'])
        self.window.ui.menu['menu.plugins'].setToolTipsVisible(True)
