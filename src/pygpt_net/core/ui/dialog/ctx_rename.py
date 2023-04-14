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

from ..widgets import RenameDialog
from ...utils import trans


class CtxRename:
    def __init__(self, window=None):
        """
        Context rename dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups ctx rename dialog"""
        id = 'ctx.rename'
        self.window.dialog[id] = RenameDialog(self.window, id)
        self.window.dialog[id].setWindowTitle(trans("dialog.ctx.rename.title"))
