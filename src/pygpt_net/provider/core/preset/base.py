#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.01 00:00:00                  #
# ================================================== #

from packaging.version import Version

from pygpt_net.item.preset import PresetItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "preset"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def create(self, item: PresetItem):
        pass

    def load(self) -> dict:
        pass

    def load_base(self) -> dict:
        pass

    def save(self, id: str, item: PresetItem):
        pass

    def save_all(self, items: dict):
        pass

    def remove(self, id: str):
        pass

    def truncate(self):
        pass

    def dump(self, item: PresetItem):
        pass

    def get_version(self):
        pass
