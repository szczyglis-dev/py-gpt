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

from typing import List, Dict, Optional

from packaging.version import Version

from pygpt_net.item.ctx import CtxMeta, CtxItem, CtxGroup


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

    def append_item(self, meta: CtxMeta, item: CtxItem) -> bool:
        pass

    def update_item(self, item: CtxItem) -> bool:
        pass

    def create(self, meta: CtxMeta) -> int:
        pass

    def load(self, id: int) -> List[CtxItem]:
        return []

    def save(self, id: int, meta: CtxMeta, items: List[CtxItem]) -> bool:
        pass

    def remove(self, id: int) -> bool:
        pass

    def remove_item(self, id: int) -> bool:
        pass

    def remove_items_from(self, meta_id: int, item_id: int) -> bool:
        pass

    def truncate(self) -> bool:
        pass

    def get_meta(
            self,
            search_string: Optional[str] = None,
            order_by: Optional[str] = None,
            order_direction: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            filters: Optional[dict] = None,
            search_content: bool = False
    ) -> Dict[int, CtxMeta]:
        pass

    def get_meta_indexed(self) -> Dict[int, CtxMeta]:
        pass

    def get_item_by_id(self, id: int) -> CtxItem:
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

    def get_groups(self) -> Dict[int, CtxGroup]:
        pass

    def insert_group(self, group: CtxGroup) -> int:
        pass

    def update_group(self, group: CtxGroup) -> bool:
        pass

    def remove_group(self, id: int, all: bool = False) -> bool:
        pass

    def truncate_groups(self) -> bool:
        pass

    def update_meta_group_id(self, meta_id: int, group_id: int) -> bool:
        pass

    def clear_meta(self, meta_id: int) -> bool:
        pass


