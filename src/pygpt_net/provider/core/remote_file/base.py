#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

from typing import Dict
from packaging.version import Version

from pygpt_net.item.store import RemoteFileItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "remote_file"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def create(self, file: RemoteFileItem):
        pass

    def load(self, id) ->  RemoteFileItem:
        pass

    def load_all(self, provider: str) -> Dict[str, RemoteFileItem]:
        pass

    def save(self, file:  RemoteFileItem):
        pass

    def save_all(self, items: Dict[str, RemoteFileItem]):
        pass

    def remove(self, id):
        pass

    def truncate(self, provider: str):
        pass

    def get_version(self) -> str:
        pass
