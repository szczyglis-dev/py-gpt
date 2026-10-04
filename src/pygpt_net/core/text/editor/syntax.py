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
from pygments.style import Style
from pygments.token import Token, Comment, Keyword, Name, String, Number, Operator, Punctuation, Generic, Error
from pygments.util import ClassNotFound


class SoftLightStyle(Style):
    """Muted editor colors with readable contrast on light surfaces."""
    styles = {
        Token: '#30343b', Comment: 'italic #7a838d',
        Keyword: '#87628b', Keyword.Constant: '#587b9b',
        Name: '#30343b', Name.Builtin: '#587b9b',
        Name.Function: '#6e6693', Name.Class: '#577f82',
        Name.Namespace: '#587b9b', Name.Decorator: '#6e6693',
        Name.Attribute: '#8d6c4b', Name.Variable: '#8d6c4b',
        String: '#5d805e', Number: '#95754e',
        Operator: '#707780', Punctuation: '#707780',
        Generic.Heading: '#587b9b', Generic.Inserted: '#5d805e',
        Generic.Deleted: '#a36363', Error: '#a36363',
    }


class PreviewLightStyle(Style):
    """Bright, lightweight syntax colors for the Files light preview."""
    styles = {
        Token: '#000000', Comment: '#606060',
        Keyword: '#ff0000', Keyword.Constant: '#005cc5',
        Keyword.Type: '#8000ff',
        Name: '#000000', Name.Builtin: '#0080ff',
        Name.Builtin.Pseudo: '#ff8000',
        Name.Function: '#8000ff', Name.Class: '#8000ff',
        Name.Namespace: '#000000', Name.Decorator: '#8000ff',
        Name.Attribute: '#000000', Name.Variable: '#8000ff',
        Name.Tag: '#008000',
        String: '#008000', Number: '#0000ff',
        Operator: '#000000', Operator.Word: '#ff0000',
        Punctuation: '#000000',
        Generic.Heading: '#0000ff', Generic.Inserted: '#008000',
        Generic.Deleted: '#b31d28', Error: '#b31d28',
    }


class SoftDarkStyle(Style):
    """Matching restrained palette for dark surfaces."""
    styles = {
        Token: '#d1d4d9', Comment: 'italic #858d98',
        Keyword: '#b59abb', Keyword.Constant: '#91abc4',
        Name: '#d1d4d9', Name.Builtin: '#91abc4',
        Name.Function: '#aaa0c7', Name.Class: '#91b4b5',
        Name.Namespace: '#91abc4', Name.Decorator: '#aaa0c7',
        Name.Attribute: '#c0a283', Name.Variable: '#c0a283',
        String: '#a2b89b', Number: '#c0aa87',
        Operator: '#a6abb3', Punctuation: '#a6abb3',
        Generic.Heading: '#91abc4', Generic.Inserted: '#a2b89b',
        Generic.Deleted: '#c49a9a', Error: '#c49a9a',
    }


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
        style = SoftDarkStyle if dark else getattr(self.editor, 'syntax_light_style', SoftLightStyle)
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
