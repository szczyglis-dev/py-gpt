#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 02:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.dialog.url import UrlDialog
from pygpt_net.utils import trans


class Url:
    def __init__(self, window=None):
        """
        URL dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup URL dialog"""
        id = 'url'
        self.window.ui.dialog[id] = UrlDialog(self.window, id)
        self.window.ui.dialog[id].setWindowTitle(trans("dialog.url.title"))
