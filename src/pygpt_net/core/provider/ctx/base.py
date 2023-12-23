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
import uuid


class BaseCtxProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "ctx"

    def init(self):
        pass

    def install(self):
        pass

    def uninstall(self):
        pass

    def is_installed(self):
        pass

    def create_id(self):
        return uuid.uuid4()

    def load(self, id):
        pass

    def save(self, id, ctx_list, ctx_items):
        pass

    def update(self):
        pass

    def remove(self, id):
        pass

    def truncate(self):
        pass

    def create(self):
        pass

    def get_list(self):
        pass

    def get_by_criteria(self):
        pass

    def count(self):
        pass
