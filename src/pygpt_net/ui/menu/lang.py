#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 05:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Lang:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup lang menu"""
        self.window.ui.menu['lang'] = {}
        self.window.ui.menu['menu.lang'] = self.window.menuBar().addMenu(trans("menu.lang"))
        self.window.ui.menu['menu.lang'].setStyleSheet(self.window.controller.theme.style('menu'))  # Windows fix
