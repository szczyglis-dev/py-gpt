#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from typing import Dict

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

    def load(self) -> Dict[str, ModelItem]:
        pass

    def load_base(self) -> Dict[str, ModelItem]:
        pass

    def save(self, items: Dict[str, ModelItem]):
        pass

    def remove(self, id: str):
        pass

    def truncate(self):
        pass

    def dump(self, model: ModelItem):
        pass

    def get_version(self) -> str:
        pass
