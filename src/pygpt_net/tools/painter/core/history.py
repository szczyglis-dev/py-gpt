#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #


from collections import deque

from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QImage


class History:
    """Painter history operations on one canvas."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.limit = 10
        self.undo_stack = deque(maxlen=self.limit)
        self.redo_stack = deque()

    def snapshot_state(self):
        """Create a full snapshot for undo."""
        canvas = self.canvas
        state = {
            'image': QImage(canvas.document.image),
            'base': QImage(canvas.document.base) if canvas.document.base is not None else None,
            'draw': QImage(canvas.document.drawing) if canvas.document.drawing is not None else None,
            'src': QImage(canvas.document.source_image) if canvas.document.source_image is not None else None,
            'canvas_size': QSize(canvas.document.canvas_size.width(), canvas.document.canvas_size.height()),
            'baseRect': QRect(canvas.document.base_rect),
        }
        return state

    def apply_state(self, state):
        """
        Apply a snapshot (used by undo/redo).

        :param state: State dict from _snapshot_state()
        """
        canvas = self.canvas
        if not state:
            return

        target_canvas_size = state.get('canvas_size', None)
        if isinstance(target_canvas_size, QSize) and target_canvas_size.isValid():
            canvas.document.canvas_size = QSize(target_canvas_size)

            canvas.document.image = QImage(state['image']) if state['image'] is not None else QImage(canvas.document.canvas_size, QImage.Format_RGB32)
            if canvas.document.image.size() != canvas.document.canvas_size:
                canvas.document.image = canvas.document.image.scaled(canvas.document.canvas_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

            if state['base'] is not None:
                canvas.document.base = QImage(state['base'])
            else:
                canvas.document.base = QImage(canvas.document.canvas_size, QImage.Format_RGB32)
                canvas.document.base.fill(Qt.white)

            if state['draw'] is not None:
                canvas.document.drawing = QImage(state['draw'])
            else:
                canvas.document.drawing = QImage(canvas.document.canvas_size, QImage.Format_ARGB32_Premultiplied)
                canvas.document.drawing.fill(Qt.transparent)

            canvas.document.source_image = QImage(state['src']) if state['src'] is not None else None
            canvas.document.base_rect = QRect(state['baseRect']) if state['baseRect'] is not None else QRect()

            canvas.document.mark_composite_dirty()
            canvas.viewport.update_widget_size_from_zoom()
            canvas.update()


    def sync_canvas_combo_after_history(self):
        canvas = self.canvas
        if canvas.window and hasattr(canvas.window, "controller"):
            canvas.tool.settings.sync_canvas_combo_from_widget()

    def push(self):
        """Save current state for undo"""
        canvas = self.canvas
        canvas.document.ensure_layers()
        canvas.document.compose()
        self.undo_stack.append(self.snapshot_state())
        self.redo_stack.clear()

    def undo(self):
        """Undo the last action, including the two-stage Text-mode history."""
        canvas = self.canvas
        # Second Undo after a committed text block was reopened for editing:
        # discard the draft and finish the transition to the pre-text state.
        if canvas.text.reopened_from_undo():
            if self.undo_stack and canvas.text.history_kind(self.undo_stack[-1]) == "text_draft_cancel":
                entry = self.undo_stack.pop()
                canvas.text.cancel(canvas, discard_undo_stage=False)
                self.apply_state(entry["state"])
                self.redo_stack.append(
                    canvas.text.make_history_entry(canvas, "text_draft_redo", entry["state"], entry["draft"])
                )
                self.sync_canvas_combo_after_history()
                return

        # A normal live text draft is not a Painter history item.
        if canvas.text.has_active():
            canvas.text.cancel(canvas)

        if not self.undo_stack:
            return

        entry = self.undo_stack[-1]
        kind = canvas.text.history_kind(entry)

        # First Undo of committed text: remove its rasterized pixels but keep
        # the action on the stack as a second stage, then reopen the block.
        if kind == "text_commit":
            current = self.snapshot_state()
            before = entry["state"]
            draft = entry["draft"]
            self.apply_state(before)
            self.undo_stack[-1] = canvas.text.make_history_entry(canvas, 
                "text_draft_cancel", before, draft
            )
            self.redo_stack.append(
                canvas.text.make_history_entry(canvas, "text_commit_redo", current, draft)
            )
            canvas.text.restore_from_history(canvas, draft)
            self.sync_canvas_combo_after_history()
            return

        current = self.snapshot_state()
        self.redo_stack.append(current)
        state = self.undo_stack.pop()
        # Defensive fallback: history-stage entries should normally be handled
        # above, but always unwrap them before applying a canvas snapshot.
        if canvas.text.history_kind(state):
            state = state.get("state")
        self.apply_state(state)
        self.sync_canvas_combo_after_history()

    def redo(self):
        """Redo the last undo action, preserving Text edit/recommit stages."""
        canvas = self.canvas
        if not self.redo_stack:
            return

        entry = self.redo_stack[-1]
        kind = canvas.text.history_kind(entry)

        # Redo after the second Text undo: restore the editable draft first.
        if kind == "text_draft_redo":
            canvas.text.cancel(canvas, discard_undo_stage=False)
            entry = self.redo_stack.pop()
            self.apply_state(entry["state"])
            self.undo_stack.append(
                canvas.text.make_history_entry(canvas, "text_draft_cancel", entry["state"], entry["draft"])
            )
            canvas.text.restore_from_history(canvas, entry["draft"])
            self.sync_canvas_combo_after_history()
            return

        # Redo after the first Text undo: close the restored editor and put the
        # already-rasterized committed state back in one operation.
        if kind == "text_commit_redo":
            entry = self.redo_stack.pop()
            before = self.snapshot_state()
            if canvas.text.has_active():
                canvas.text.cancel(canvas, discard_undo_stage=False)
            if self.undo_stack and canvas.text.history_kind(self.undo_stack[-1]) == "text_draft_cancel":
                stage = self.undo_stack.pop()
                before = stage["state"]
            self.apply_state(entry["state"])
            self.undo_stack.append(
                canvas.text.make_history_entry(canvas, "text_commit", before, entry["draft"])
            )
            self.sync_canvas_combo_after_history()
            return

        canvas.text.cancel(canvas)
        current = self.snapshot_state()
        self.undo_stack.append(current)
        state = self.redo_stack.pop()
        if canvas.text.history_kind(state):
            state = state.get("state")
        self.apply_state(state)
        self.sync_canvas_combo_after_history()

    def can_undo(self) -> bool:
        """
        Check if undo is available

        :return: True if undo is available
        """
        canvas = self.canvas
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        """
        Check if redo is available

        :return: True if redo is available
        """
        canvas = self.canvas
        return bool(self.redo_stack)

