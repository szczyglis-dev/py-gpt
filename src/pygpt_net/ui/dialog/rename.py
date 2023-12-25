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

from pygpt_net.ui.widget.dialog.rename import RenameDialog
from pygpt_net.utils import trans


class Rename:
    def __init__(self, window=None):
        """
        Context rename dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup rename dialog"""
        id = 'rename'
        self.window.ui.dialog[id] = RenameDialog(self.window, id)
        self.window.ui.dialog[id].setWindowTitle(trans("dialog.rename.title"))
