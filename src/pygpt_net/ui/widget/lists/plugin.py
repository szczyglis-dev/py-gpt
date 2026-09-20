#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 08:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.lists.base import BaseList


class PluginList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Plugin select menu (in settings dialog)

        :param window: main window
        :param id: parent id
        """
        super(PluginList, self).__init__(window)
        self.window = window
        self.id = id

    def click(self, val):
        plugin_id = val.data(Qt.UserRole)
        if plugin_id:
            idx = self.window.controller.plugins.get_tab_idx(plugin_id)
        else:
            # Compatibility fallback for an older list model.
            idx = val.row()
        if idx is None:
            return
        self.window.ui.tabs['plugin.settings'].setCurrentIndex(idx)
        self.window.controller.plugins.set_by_tab(idx)

