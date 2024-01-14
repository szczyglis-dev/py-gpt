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

from packaging.version import Version

from pygpt_net.item.model import ModelItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "model"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def create(self, model: ModelItem) -> str:
        pass

    def load(self) -> dict:
        pass

    def load_base(self) -> dict:
        pass

    def save(self, items: dict):
        pass

    def remove(self, id: str):
        pass

    def truncate(self):
        pass

    def dump(self, model: ModelItem):
        pass

    def get_version(self) -> str:
        pass
