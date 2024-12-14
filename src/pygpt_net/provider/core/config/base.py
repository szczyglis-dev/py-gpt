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

from typing import Dict, Any, Optional

from packaging.version import Version


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "config"
        self.path = None
        self.path_app = None
        self.meta = None

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def load(self, all: bool = False) -> Optional[Dict[str, Any]]:
        pass

    def load_base(self) -> Optional[Dict[str, Any]]:
        pass

    def save(self, items: Dict[str, Any], filename: str = 'config.json'):
        pass

    def get_options(self) -> Optional[Dict[str, Any]]:
        pass

    def get_sections(self) -> Optional[Dict[str, Any]]:
        pass

    def get_version(self) -> str:
        pass
