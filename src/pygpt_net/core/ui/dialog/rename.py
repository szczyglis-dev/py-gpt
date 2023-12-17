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

from ..widget.dialog import RenameDialog
from ...utils import trans


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
        self.window.dialog[id] = RenameDialog(self.window, id)
        self.window.dialog[id].setWindowTitle(trans("dialog.rename.title"))
