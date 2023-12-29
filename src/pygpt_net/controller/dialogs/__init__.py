#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #


from .confirm import Confirm
from .debug import Debug
from .info import Info


class Dialogs:
    def __init__(self, window=None):
        """
        Dialogs controller

        :param window: Window instance
        """
        self.window = window
        self.confirm = Confirm(window)
        self.debug = Debug(window)
        self.info = Info(window)

    def setup(self):
        """Setup dialogs"""
        self.info.setup()
