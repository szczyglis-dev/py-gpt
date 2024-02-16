#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.16 16:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.dialog.snap import SnapDialog


class Snap:
    def __init__(self, window=None):
        """
        Snap dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup snap dialog"""
        self.window.ui.dialog['snap'] = SnapDialog(self.window)
