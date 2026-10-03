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
"""One note: content operations, view state and persistence."""
import time
from PySide6.QtGui import QTextCursor

class Document:
    def __init__(self, tool, item, writer):
        self.tool = tool
        self.item = item
        self.writer = writer
        self.widget = None
        self.loading = False
        self.closed = False
        self.opened = False

    def restore(self):
        self.loading = True
        try:
            self.widget.setText(self.item.content)
            editor = self.widget.textarea
            editor.markers.restore(self.item.highlights)
            if self.item.scroll_pos not in (None, -1):
                editor.view.set_scroll(self.item.scroll_pos)
        finally:
            editor.save_timer.stop()
            self.loading = False

    def save(self):
        if self.loading or self.closed:
            return False
        if self.widget is not None:
            editor = self.widget.textarea
            editor.save_timer.stop()
            self.item.content = editor.toPlainText()
            self.item.highlights = editor.markers.ranges()
            if editor.initialized:
                self.item.scroll_pos = editor.view.scroll()
            tab = self.widget.tab
            if tab is not None:
                self.item.title = tab.title
            self.item.initialized = True
        self.item.updated = int(time.time())
        self.writer.save(self.item)
        return True

    def text(self):
        return self.widget.toPlainText() if self.widget is not None else self.item.content

    def append(self, text):
        text = text.strip()
        if self.widget is None:
            self.item.content += ('\n' if self.item.content.strip() else '') + text
        else:
            editor = self.widget.textarea
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(('\n' if self.text().strip() else '') + text)
            editor.setTextCursor(cursor)
        self.save()

    def clear(self):
        if self.widget is None:
            self.item.content = ''
            self.item.highlights = []
            self.item.scroll_pos = -1
        else:
            self.widget.textarea.clear()
            self.widget.textarea.markers.clear(persist=False)
        self.save()

    def close(self):
        if self.closed:
            return
        self.save()
        self.closed = True
        if self.widget is not None:
            self.widget.textarea.on_delete()
        self.tool.unregister_surface(self)
        if self.tool.documents.opened.get(self.item.idx) is self:
            self.tool.documents.opened.pop(self.item.idx)
        self.widget = None
