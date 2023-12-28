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


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "ctx"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version):
        pass

    def append_item(self, meta, item):
        pass

    def update_item(self, item):
        pass

    def create(self, meta):
        pass

    def load(self, id):
        return []

    def save(self, id, meta, items):
        pass

    def remove(self, id):
        pass

    def truncate(self):
        pass

    def get_meta(self):
        pass

    def dump(self, ctx):
        pass
