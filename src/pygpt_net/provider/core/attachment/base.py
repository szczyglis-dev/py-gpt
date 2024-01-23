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

from pygpt_net.item.attachment import AttachmentItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "attachment"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def create(self, attachment: AttachmentItem) -> str:
        pass

    def load(self) -> dict:
        pass

    def save(self, items: dict):
        pass

    def remove(self, id: str):
        pass

    def truncate(self, mode: str):
        pass

    def dump(self, attachment: AttachmentItem) -> str:
        pass
