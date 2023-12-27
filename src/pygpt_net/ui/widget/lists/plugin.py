#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.lists.base import BaseList


class PluginList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Plugin select menu (in settings dialog)

        :param window: main window
        :param id: input id
        """
        super(PluginList, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)

    def click(self, val):
        idx = val.row()
        self.window.ui.tabs['plugin.settings'].setCurrentIndex(idx)
        self.window.controller.plugins.set_by_tab(idx)

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.presets.editor.edit(val.row())
