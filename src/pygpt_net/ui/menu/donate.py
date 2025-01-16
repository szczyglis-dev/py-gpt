#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.16 01:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class Donate:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup donate menu"""
        self.window.ui.menu['donate.coffee'] = QAction(QIcon(":/icons/favorite.svg"), "Buy me a coffee",
                                                    self.window)
        self.window.ui.menu['donate.coffee'].setMenuRole(QAction.MenuRole.NoRole)
        self.window.ui.menu['donate.paypal'] = QAction(QIcon(":/icons/favorite.svg"), "PayPal",
                                                        self.window)
        self.window.ui.menu['donate.github'] = QAction(QIcon(":/icons/favorite.svg"), "GitHub Sponsors", self.window)

        self.window.ui.menu['donate.coffee'].triggered.connect(
            lambda: self.window.controller.dialogs.info.donate('coffee'))
        self.window.ui.menu['donate.paypal'].triggered.connect(
            lambda: self.window.controller.dialogs.info.donate('paypal'))
        self.window.ui.menu['donate.github'].triggered.connect(
            lambda: self.window.controller.dialogs.info.donate('github'))

        self.window.ui.menu['menu.donate'] = self.window.menuBar().addMenu(trans("menu.info.donate"))
        self.window.ui.menu['menu.donate'].addAction(self.window.ui.menu['donate.coffee'])
        self.window.ui.menu['menu.donate'].addAction(self.window.ui.menu['donate.paypal'])
        self.window.ui.menu['menu.donate'].addAction(self.window.ui.menu['donate.github'])
