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


class BaseCtxProvider:
    def __init__(self):
        self.id = ""
        self.type = "ctx"

    def init(self):
        pass

    def load(self):
        pass

    def save(self):
        pass

    def update(self):
        pass

    def remove(self):
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
