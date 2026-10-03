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
"""Persistent, undoable text markers for one editor."""
from PySide6.QtGui import QColor, QTextCursor, QTextCharFormat
from ..ui.highlight import MarkerHighlighter, MARKER_PROPERTY, marked_ranges

class Markers:
    def __init__(self, editor):
        self.editor = editor
        self.highlighter = MarkerHighlighter(editor.document(), self.colors)

    def mark(self):
        """Apply highlight to current selection"""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return
        start = min(cursor.selectionStart(), cursor.selectionEnd())
        end = max(cursor.selectionStart(), cursor.selectionEnd())
        self.add((start, end - start))
        self.highlighter.rehighlight()
        self.editor.persist()

    def unmark(self):
        """Remove highlight from current selection"""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return
        start = min(cursor.selectionStart(), cursor.selectionEnd())
        end = max(cursor.selectionStart(), cursor.selectionEnd())
        self.remove(start, end - start)
        self.highlighter.rehighlight()
        self.editor.persist()

    def ranges(self):
        """Serialize live marker positions in the existing (start, length) format."""
        ranges = []
        block = self.editor.document().begin()
        while block.isValid():
            ranges.extend(marked_ranges(block))
            block = block.next()
        return self.merge(ranges)

    def restore(self, highlights):
        """Restore persisted ranges as text metadata, without creating undo steps."""
        ranges = self.merge(self.sanitize(highlights))
        if ranges == self.ranges():
            return
        document = self.editor.document()
        undo_enabled = document.isUndoRedoEnabled()
        document.setUndoRedoEnabled(False)
        try:
            self.format(0, document.characterCount() - 1, False)
            for start, length in ranges:
                self.format(start, length, True)
        finally:
            document.setUndoRedoEnabled(undo_enabled)
        self.highlighter.rehighlight()

    def clear(self, persist: bool = True):
        """Clear all highlights (undoable like other formatting actions)."""
        self.format(0, self.editor.document().characterCount() - 1, False)
        fmt = self.editor.currentCharFormat()
        fmt.setProperty(MARKER_PROPERTY, False)
        self.editor.setCurrentCharFormat(fmt)
        self.highlighter.rehighlight()
        if persist:
            self.editor.persist()

    def colors(self):
        """
        Return (text_color, background_color) for highlights based on current theme.
        """
        is_dark = self.is_dark()
        if is_dark:
            text_color = QColor(0, 0, 0)
            bg_color = QColor(255, 255, 0)  # yellow
        else:
            text_color = QColor(0, 0, 0)
            bg_color = QColor(255, 255, 0)  # yellow
        return text_color, bg_color

    def apply_theme(self):
        """
        Public method to refresh highlight colors. Can be called by theme controller
        after theme switch.
        """
        try:
            self.highlighter.rehighlight()
        except Exception:
            pass

    def is_dark(self) -> bool:
        """
        Get whether current theme is dark
        """
        return self.editor.window.controller.theme.is_dark_theme()

    def sanitize(self, ranges):
        """Sanitize ranges to (start>=0, length>0) integers"""
        out = []
        for r in ranges or []:
            try:
                s = int(r[0])
                l = int(r[1])
            except Exception:
                continue
            if s < 0 or l <= 0:
                continue
            out.append((s, l))
        out.sort(key=lambda x: x[0])
        return out

    def merge(self, ranges):
        """Merge overlapping/adjacent ranges"""
        if not ranges:
            return []
        merged = []
        for s, l in ranges:
            if not merged:
                merged.append([s, s + l])
                continue
            ps, pe = merged[-1]
            se = s + l
            if s <= pe:
                merged[-1][1] = max(pe, se)
            else:
                merged.append([s, se])
        return [(s, e - s) for s, e in merged]

    def format(self, start, length, enabled):
        """Native character properties follow edits, including undo and redo."""
        end = min(start + length, self.editor.document().characterCount() - 1)
        start = max(0, start)
        if start >= end:
            return
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setProperty(MARKER_PROPERTY, enabled)
        cursor.mergeCharFormat(fmt)

    def add(self, rng):
        start, length = int(rng[0]), int(rng[1])
        if length <= 0:
            return
        self.format(start, length, True)
        self.editor.schedule_save()

    def remove(self, start, length):
        if length <= 0:
            return
        self.format(start, length, False)
        self.editor.schedule_save()

    def overlaps(self, start, end):
        return any(hs < end and hs + length > start for hs, length in self.ranges())

