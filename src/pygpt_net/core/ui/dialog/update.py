#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

from ..widgets import UpdateDialog


class Update:
    def __init__(self, window=None):
        """
        Updater dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups updater dialog"""
        self.window.dialog['update'] = UpdateDialog(self.window)
