#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.21 20:00:00                  #
# ================================================== #

from PySide6.QtGui import (
    QTextCharFormat,
    QSyntaxHighlighter,
)


class MarkerHighlighter(QSyntaxHighlighter):
    def __init__(self, document, ranges_provider, colors_provider):
        """
        Syntax highlighter for marking ranges.

        :param document: QTextDocument
        :param ranges_provider: callable returning list of (start, length)
        :param colors_provider: callable returning (text_color: QColor|None, bg_color: QColor|None)
        """
        super().__init__(document)
        self._ranges_provider = ranges_provider
        self._colors_provider = colors_provider

    def set_colors_provider(self, colors_provider):
        """Set a new provider for highlight colors"""
        self._colors_provider = colors_provider
        self.rehighlight()

    def highlightBlock(self, text: str):
        """Apply formatting to ranges intersecting current block"""
        ranges = self._ranges_provider() or []
        if not ranges:
            return

        text_color, bg_color = (None, None)
        try:
            text_color, bg_color = self._colors_provider()
        except Exception:
            pass

        fmt = QTextCharFormat()
        if bg_color is not None:
            fmt.setBackground(bg_color)
        if text_color is not None:
            fmt.setForeground(text_color)

        block_start = self.currentBlock().position()
        block_len = len(text)
        for s, l in ranges:
            if l <= 0:
                continue
            rel_start = s - block_start
            rel_end = (s + l) - block_start
            if rel_end <= 0 or rel_start >= block_len:
                continue
            rel_start = max(0, rel_start)
            length = min(block_len - rel_start, rel_end - rel_start)
            if length > 0:
                self.setFormat(rel_start, length, fmt)