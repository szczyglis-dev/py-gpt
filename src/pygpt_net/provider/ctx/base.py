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

from pygpt_net.item.ctx import CtxMeta, CtxItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "ctx"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def append_item(self, meta: CtxMeta, item: CtxItem):
        pass

    def update_item(self, item: CtxItem):
        pass

    def create(self, meta: CtxMeta):
        pass

    def load(self, id) -> list:
        return []

    def save(self, id, meta: CtxMeta, items: list):
        pass

    def remove(self, id):
        pass

    def truncate(self):
        pass

    def get_meta(self, search_string: str = None, order_by: str = None, order_direction: str = None,
                 limit: int = None, offset: int = None):
        pass

    def dump(self, ctx: CtxItem):
        pass
