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

from typing import Optional, Dict

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

    def load(self) -> Optional[Dict[str, PresetItem]]:
        pass

    def load_base(self) -> Optional[Dict[str, PresetItem]]:
        pass

    def save(self, id: str, item: PresetItem):
        pass

    def save_all(self, items: Dict[str, PresetItem]):
        pass

    def remove(self, id: str):
        pass

    def truncate(self):
        pass

    def dump(self, item: PresetItem):
        pass

    def get_version(self):
        pass
