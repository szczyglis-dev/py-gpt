#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

from typing import List
from dataclasses import dataclass, field

from pygpt_net.item.ctx import CtxItem


@dataclass(slots=True)
class Bag:
    window: object = None
    meta: object = None
    tab_id: int = 0
    items: List[CtxItem] = field(default_factory=list)

    def __init__(self, window=None):
        """
        Context bag

        :param window: Window instance
        """
        self.window = window
        self.meta = None  # current meta
        self.tab_id = 0
        self.items = []

    def get_items(self) -> List[CtxItem]:
        """
        Return ctx items

        :return: ctx items
        """
        return self.items

    def set_items(self, items: List[CtxItem]):
        """
        Set ctx items

        :param items: ctx items
        """
        self.clear_items()
        self.items = items

    def clear_items(self):
        """Clear items"""
        self.items.clear()
        self.items = []

    def count_items(self) -> int:
        """
        Count ctx items

        :return: items count
        """
        return len(self.items)