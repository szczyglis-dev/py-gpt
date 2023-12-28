#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.27 14:00:00                  #
# ================================================== #

class BaseMigration:
    def __init__(self, window=None):
        self.window = window

    def up(self, conn):
        pass
