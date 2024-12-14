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

from pygpt_net.item.mode import ModeItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "mode"

    def attach(self, window):
        self.window = window

    def create(self, mode: ModeItem) -> str:
        pass

    def load(self) -> Dict[str, str]:
        pass

    def save(self, items: Dict[str, str]):
        pass

    def remove(self, id: str):
        pass

    def truncate(self):
        pass

    def dump(self, mode: ModeItem) -> str:
        pass

    def get_version(self) -> str:
        pass
