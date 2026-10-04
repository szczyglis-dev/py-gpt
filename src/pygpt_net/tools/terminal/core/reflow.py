#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #\
"""Rebuild physical terminal rows from logical lines on a viewport resize."""
from pyte.screens import StaticDefaultDict


def reflow(screen, lines, columns):
    history = list(screen.history.top)
    last = max([screen.cursor.y] + [y for y, row in screen.buffer.items()
                                  if any(cell.data.strip() for cell in row.values())])
    physical = history + [screen.buffer[y] for y in range(last + 1)]
    cursor_row = len(history) + screen.cursor.y
    logical = []
    cells = []
    cursor_line, cursor_offset = 0, 0
    for index, row in enumerate(physical):
        wrap = getattr(row, 'wrap_width', None)
        length = wrap or max([0] + [x + 1 for x, cell in row.items()
                                  if cell != row.default])
        if index == cursor_row:
            cursor_line = len(logical)
            cursor_offset = len(cells) + screen.cursor.x
            length = max(length, screen.cursor.x)
        cells.extend(row[x] for x in range(length))
        if not wrap:
            logical.append(cells)
            cells = []
    if cells:
        logical.append(cells)
    rebuilt = []
    new_cursor_row, new_cursor_x = 0, 0
    cursor_origin = 0
    for index, cells in enumerate(logical):
        start = len(rebuilt)
        for offset in range(0, max(1, len(cells)), columns):
            row = StaticDefaultDict(screen.default_char)
            row.update(enumerate(cells[offset:offset + columns]))
            row.wrap_width = columns if offset + columns < len(cells) else None
            rebuilt.append(row)
        if index == cursor_line:
            cursor_origin = start
            new_cursor_row = start + cursor_offset // columns
            new_cursor_x = cursor_offset % columns
            if cursor_offset and new_cursor_x == 0:
                new_cursor_row -= 1
                new_cursor_x = columns  # VT delayed wrap, not the next row yet.
    start = min(new_cursor_row, max(0, len(rebuilt) - lines))
    screen.history.top.clear()
    screen.history.top.extend(rebuilt[:start])
    screen.buffer.clear()
    screen.buffer.update(enumerate(rebuilt[start:]))
    screen.lines, screen.columns = lines, columns
    screen.cursor.y = new_cursor_row - start
    screen.cursor.x = new_cursor_x
    screen.set_margins()
    screen.dirty.update(range(lines))

    screen.redraw_origin = max(0, cursor_origin - start)
    screen.redraw_pending = (2004 << 5) in screen.mode
