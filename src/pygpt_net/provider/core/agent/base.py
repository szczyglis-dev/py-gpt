#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

from typing import Dict, Any

from packaging.version import Version

from pygpt_net.item.agent import AgentItem
from pygpt_net.item.builder_layout import BuilderLayoutItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "agent"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def create(self, assistant: AgentItem) -> str:
        pass

    def load(self) -> Dict[str, Any]:
        pass

    def save(self, layout: BuilderLayoutItem, agents: Dict[str, AgentItem]):
        pass

    def remove(self, id: str):
        pass

    def truncate(self):
        pass

    def dump(self, agent: AgentItem) -> str:
        pass
