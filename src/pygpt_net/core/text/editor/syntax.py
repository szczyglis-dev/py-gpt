#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.29 10:00:00                  #
# ================================================== #

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound


class SyntaxHighlighter(QSyntaxHighlighter):
    """Pygments-backed multiline syntax highlighter."""

    def __init__(self, document, path, editor):
        super().__init__(document)
        self.editor = editor
        self.lexer = TextLexer(stripnl=False, ensurenl=False)
        self.formats = {}
        self.spans = {}
        self._signature = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.refresh)
        document.contentsChange.connect(self._on_contents_change)
        self.set_path(path)

    def _on_contents_change(self, pos, removed, added):
        if removed or added:
            # Initial refreshes use start(0), which changes the stored interval.
            # Restore the debounce instead of lexing the document on every key.
            self.timer.start(180)

    def set_path(self, path):
        """Select a lexer from the current file path and refresh highlighting."""
        try:
            self.lexer = get_lexer_for_filename(path, stripnl=False, ensurenl=False) if path else TextLexer(
                stripnl=False,
                ensurenl=False,
            )
        except ClassNotFound:
            self.lexer = TextLexer(stripnl=False, ensurenl=False)
        self._signature = None
        self.timer.start(0)

    def refresh(self):
        dark = self.editor.palette().base().color().lightness() < 128
        signature = (self.document().toPlainText(), dark, self.lexer.__class__)
        if signature == self._signature:
            return
        self._signature = signature
        self.formats = {}
        style = get_style_by_name('monokai' if dark else 'default')
        self.spans = {}
        line, column = 0, 0
        for token, value in lex(self.document().toPlainText(), self.lexer):
            if token not in self.formats:
                spec = style.style_for_token(token)
                fmt = QTextCharFormat()
                if spec['color']:
                    fmt.setForeground(QColor('#' + spec['color']))
                fmt.setFontItalic(spec['italic'])
                self.formats[token] = fmt
            parts = value.split('\n')
            for idx, part in enumerate(parts):
                # Qt positions count UTF-16 code units, not Python code points.
                length = len(part.encode('utf-16-le')) // 2
                self.spans.setdefault(line, []).append((column, length, self.formats[token]))
                column += length
                if idx < len(parts) - 1:
                    line += 1
                    column = 0
        self.rehighlight()

    def highlightBlock(self, text):
        for start, length, fmt in self.spans.get(self.currentBlock().blockNumber(), []):
            self.setFormat(start, length, fmt)
