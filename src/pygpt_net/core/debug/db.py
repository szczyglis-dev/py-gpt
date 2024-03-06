#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 02:00:00                  #
# ================================================== #

import datetime
import os


class DatabaseDebug:
    def __init__(self, window=None):
        """
        DB debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'db'

    def update(self):
        """Update db window."""
        pass
