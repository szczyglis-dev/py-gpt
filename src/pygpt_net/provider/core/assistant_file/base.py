#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

from packaging.version import Version

from pygpt_net.item.assistant import AssistantFileItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "assistant_file"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def create(self, file: AssistantFileItem):
        pass

    def load(self, id) ->  AssistantFileItem:
        pass

    def load_all(self) -> dict:
        pass

    def save(self, file:  AssistantFileItem):
        pass

    def save_all(self, items: dict):
        pass

    def remove(self, id):
        pass

    def truncate(self):
        pass

    def get_version(self) -> str:
        pass
