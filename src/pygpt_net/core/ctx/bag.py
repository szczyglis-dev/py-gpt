#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

class Bag:
    def __init__(self, window=None):
        """
        Context bag
        """
        self.window = window
        self.meta = None  # current meta
        self.tab_id = 0
        self.items = []

    def get_items(self):
        return self.items

    def set_items(self, items):
        self.items = items

    def clear_items(self):
        self.items = []

    def count_items(self):
        return len(self.items)