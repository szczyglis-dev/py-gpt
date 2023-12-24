#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 19:00:00                  #
# ================================================== #


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "notepad"

    def install(self):
        pass

    def create(self, notepad):
        pass

    def load(self, id):
        pass

    def load_all(self):
        pass

    def save(self, notepad):
        pass

    def save_all(self, items):
        pass

    def remove(self, id):
        pass

    def truncate(self):
        pass

    def get_version(self):
        pass
