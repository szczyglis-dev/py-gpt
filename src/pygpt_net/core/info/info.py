#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

class Info:
    def __init__(self, window=None):
        """
        Info core

        :param window main window
        """
        self.window = window

        # prepare info ids
        self.ids = ['about', 'changelog']
        self.active = {}

        # prepare active
        for id in self.ids:
            self.active[id] = False
