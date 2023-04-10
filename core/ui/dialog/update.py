#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from core.ui.widgets import UpdateDialog


class Update:
    def __init__(self, window=None):
        self.window = window

    def setup(self):
        """Setup update dialog"""
        self.window.dialog['update'] = UpdateDialog(self.window)
