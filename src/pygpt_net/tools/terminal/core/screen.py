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
"""VT screen extensions for applications using a separate fullscreen buffer."""
import copy
import pyte
from pyte import modes


class TerminalScreen(pyte.HistoryScreen):
    def __init__(self, *args, **kwargs):
        self.primary = None
        self.redraw_pending = False
        self.redraw_origin = 0
        super().__init__(*args, **kwargs)

    def set_mode(self, *modes, **kwargs):
        if kwargs.get('private') and any(mode in (47, 1047, 1049) for mode in modes):
            if self.primary is None:
                self.primary = (copy.deepcopy(self.buffer), copy.deepcopy(self.cursor), copy.deepcopy(self.history), self.lines, self.columns)
                self.reset()
        super().set_mode(*modes, **kwargs)

    def reset_mode(self, *modes, **kwargs):
        if kwargs.get('private') and any(mode in (47, 1047, 1049) for mode in modes):
            if self.primary is not None:
                rows, columns = self.lines, self.columns
                self.buffer, self.cursor, self.history, self.lines, self.columns = self.primary
                self.primary = None
                self.resize(lines=rows, columns=columns)
                self.dirty.update(range(self.lines))
        super().reset_mode(*modes, **kwargs)

    def draw(self, data):
        # Attach wrap information to row objects so it follows scrolling into
        # history. Explicit linefeeds remain separate logical lines.
        self.redraw_pending = False
        for char in data:
            if self.cursor.x == self.columns and modes.DECAWM in self.mode:
                self.buffer[self.cursor.y].wrap_width = self.columns
            super().draw(char)

    def erase_in_line(self, how=0, *args, **kwargs):
        if how == 0 and self.cursor.x == 0 and self.redraw_pending:
            # Readline repaints its entire logical prompt with CR + EL after
            # SIGWINCH. Reflow may have moved the cursor to a continuation row.
            # Apply that repaint at the prompt origin, not halfway through it.
            for y in range(self.redraw_origin, self.cursor.y + 1):
                self.buffer.pop(y, None)
            self.cursor.y = self.redraw_origin
            self.redraw_pending = False
        row = self.buffer[self.cursor.y]
        if how in (0, 2):
            row.wrap_width = None
        super().erase_in_line(how, *args, **kwargs)

    def erase_in_display(self, how=0, *args, **kwargs):
        for y, row in self.buffer.items():
            if how in (2, 3) or (how == 0 and y >= self.cursor.y) or (how == 1 and y <= self.cursor.y):
                row.wrap_width = None
        super().erase_in_display(how, *args, **kwargs)

    def resize(self, lines=None, columns=None):
        """Reflow soft-wrapped logical lines, keeping colors and cursor offset."""
        lines, columns = lines or self.lines, columns or self.columns
        if (lines, columns) == (self.lines, self.columns):
            return
        if self.primary is not None:
            # Fullscreen applications own cell coordinates and redraw on SIGWINCH.
            super().resize(lines=lines, columns=columns)
            self.cursor.y = min(self.cursor.y, lines - 1)
            self.cursor.x = min(self.cursor.x, columns - 1)
            return
        from .reflow import reflow
        reflow(self, lines, columns)
