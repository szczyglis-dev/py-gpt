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
    QTextFormat,
)


MARKER_PROPERTY = QTextFormat.UserProperty + 1


def marked_ranges(block):
    """Yield Qt/UTF-16 positions from persistent character formatting."""
    fragment_it = block.begin()
    while not fragment_it.atEnd():
        fragment = fragment_it.fragment()
        if fragment.isValid() and fragment.charFormat().boolProperty(MARKER_PROPERTY):
            yield fragment.position(), fragment.length()
        fragment_it += 1
    # Qt stores the paragraph separator's format on the following block.
    following = block.next()
    if following.isValid() and following.charFormat().boolProperty(MARKER_PROPERTY):
        yield following.position() - 1, 1


class MarkerHighlighter(QSyntaxHighlighter):
    def __init__(self, document, colors_provider):
        super().__init__(document)
        self._colors_provider = colors_provider

    def set_colors_provider(self, colors_provider):
        """Set a new provider for highlight colors."""
        self._colors_provider = colors_provider
        self.rehighlight()

    def highlightBlock(self, text: str):
        """Render marker metadata without changing the document or undo history."""
        text_color, bg_color = self._colors_provider()
        fmt = QTextCharFormat()
        if bg_color is not None:
            fmt.setBackground(bg_color)
        if text_color is not None:
            fmt.setForeground(text_color)
        block = self.currentBlock()
        for start, length in marked_ranges(block):
            relative = start - block.position()
            length = min(length, block.length() - 1 - relative)
            if length > 0:
                self.setFormat(relative, length, fmt)
