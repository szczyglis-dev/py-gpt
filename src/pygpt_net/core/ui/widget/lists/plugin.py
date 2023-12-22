#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 19:00:00                  #
# ================================================== #

from .base import SelectMenu


class PluginSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Plugin select menu (in settings dialog)

        :param window: main window
        :param id: input id
        """
        super(PluginSelectMenu, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)

    def click(self, val):
        idx = val.row()
        self.window.ui.tabs['plugin.settings'].setCurrentIndex(idx)
        self.window.controller.plugins.set_plugin_by_tab(idx)

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.presets.edit(val.row())
