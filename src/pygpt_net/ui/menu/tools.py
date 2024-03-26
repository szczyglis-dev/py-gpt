#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.26 10:00:00                  #
# ================================================== #

from pygpt_net.utils import trans
import pygpt_net.icons_rc

class Tools:
    def __init__(self, window=None):
        """
        Tools menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup tools menu"""
        actions = self.window.tools.setup_menu_actions()
        if len(actions) == 0:
            return
        self.window.ui.menu['menu.tools'] = self.window.menuBar().addMenu(trans("menu.tools"))
        for key in actions:
            self.window.ui.menu[key] = actions[key]
            self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu[key])
