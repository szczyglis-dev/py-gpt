#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.08 03:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.dialog.find import FindDialog
from pygpt_net.utils import trans


class Find:
    def __init__(self, window=None):
        """
        Find dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup find dialog"""
        id = 'find'
        self.window.ui.dialog[id] = FindDialog(self.window, id)
        self.window.ui.dialog[id].setWindowTitle(trans("dialog.find.title"))
