#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 02:00:00                  #
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

    def remove_item(self, id):
        pass

    def truncate(self):
        pass

    def get_meta(
            self,
            search_string: str = None,
            order_by: str = None,
            order_direction: str = None,
            limit: int = None,
            offset: int = None,
            filters: dict = None,
            search_content: bool = False
    ):
        pass

    def get_meta_indexed(self):
        pass

    def dump(self, ctx: CtxItem):
        pass

    def set_meta_indexed_by_id(self, id: int, ts: int) -> bool:
        pass

    def update_meta_indexes_by_id(self, id: int, meta: CtxMeta) -> bool:
        pass

    def update_meta_indexed_by_id(self, id: int) -> bool:
        pass

    def update_meta_indexed_to_ts(self, ts: int) -> bool:
        pass

    def clear_meta_indexed_by_id(self, id: int) -> bool:
        pass

    def clear_meta_indexed_all(self) -> bool:
        pass
