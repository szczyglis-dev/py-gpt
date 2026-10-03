#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Document registry; documents stay independent of their Qt tabs."""
from .document import Document

class Documents:
    def __init__(self, tool):
        self.tool = tool
        self.opened = {}

    @property
    def widgets(self):
        return {idx: document.widget for idx, document in self.opened.items()
                if document.widget is not None}

    def create(self, idx=None):
        item = self.tool.storage.allocate(idx)
        if item.idx in self.opened:
            raise ValueError(f'Notepad {item.idx} is already open')
        document = Document(self.tool, item, self.tool.storage.writer())
        self.opened[item.idx] = document
        return document

    def get(self, idx=None):
        if idx is None:
            idx = self.tool.tabs.current()
        document = self.opened.get(idx)
        if document is not None:
            return document
        item = self.tool.storage.get_by_id(idx)
        if item is not None:
            return Document(self.tool, item, self.tool.storage.writer())
        return None

    def append(self, text, idx=None):
        document = self.get(idx)
        if document is not None:
            document.append(text)
            return True
        return False

    def clear(self, idx=None):
        document = self.get(idx)
        if document is not None:
            document.clear()
            return True
        return False

    def text(self, idx=None):
        document = self.get(idx)
        return document.text() if document is not None else ''

    def save_all(self):
        for document in tuple(self.opened.values()):
            document.save()

    def rename(self, idx, title):
        document = self.get(idx)
        if document is None:
            return False
        document.item.title = title
        for tab in self.tool.tabs.all():
            if tab.data_id == idx:
                self.tool.window.core.tabs.update_title(tab.idx, title, title, tab.column_idx)
        document.save()
        return True
