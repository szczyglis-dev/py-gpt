#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.lists.base import BaseList


class ModelList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(ModelList, self).__init__(window)
        self.window = window
        self.id = id

    def click(self, val):
        self.window.controller.model.select(val.row())
        self.selection = self.selectionModel().selection()
