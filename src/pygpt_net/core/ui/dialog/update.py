#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

from ..widget.dialog import UpdateDialog


class Update:
    def __init__(self, window=None):
        """
        Updater dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup updater dialog"""
        self.window.ui.dialog['update'] = UpdateDialog(self.window)
