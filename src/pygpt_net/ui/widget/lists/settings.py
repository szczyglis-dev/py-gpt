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

from pygpt_net.ui.widget.lists.base import BaseList


class SettingsSectionList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Settings section menu (in settings dialog)

        :param window: main window
        :param id: settings id
        """
        super(SettingsSectionList, self).__init__(window)
        self.window = window
        self.id = id

    def click(self, val):
        idx = val.row()
        self.window.ui.tabs['settings.section'].setCurrentIndex(idx)
        self.window.controller.settings.set_by_tab(idx)
