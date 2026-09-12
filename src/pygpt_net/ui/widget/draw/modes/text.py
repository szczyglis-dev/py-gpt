#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.12 15:55:00                  #
# ================================================== #

import math

from PySide6.QtCore import Qt, QPoint, QRect, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QWidget

from .base import BaseDrawMode, DrawMode


class PainterTextEdit(QPlainTextEdit):
    """Lightweight in-place editor used by Painter Text mode."""

    def __init__(self, painter, mode):
        super().__init__(painter)
        self.painter = painter
        self.mode = mode
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet(
            "QPlainTextEdit { background: transparent; "
            "border: 1px dashed rgba(128, 128, 128, 170); padding: 2px; }"
        )
        # QTextDocument can emit textChanged before its layout is fully updated.
        # Coalesce geometry work to the next event-loop turn so the editor frame
        # follows inserts/deletes without clipping.
        self.textChanged.connect(lambda: self.mode.schedule_geometry_sync(self.painter))

    def event(self, event):
        # Claim native text-editing shortcuts before Painter-wide QActions see them.
        if event.type() == event.Type.ShortcutOverride:
            if (
                event.matches(QKeySequence.StandardKey.Copy)
                or event.matches(QKeySequence.StandardKey.Paste)
                or event.matches(QKeySequence.StandardKey.Cut)
                or event.matches(QKeySequence.StandardKey.Undo)
                or event.matches(QKeySequence.StandardKey.Redo)
                or event.matches(QKeySequence.StandardKey.SelectAll)
                or event.key() in (Qt.Key_Delete, Qt.Key_Backspace)
            ):
                event.accept()
                return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.mode.cancel(self.painter)
            event.accept()
            return

        # A text block reopened by Painter Undo is a dedicated history stage:
        # the next Undo removes the whole draft instead of invoking the local
        # QPlainTextEdit character undo stack.
        if self.mode.reopened_from_undo():
            if event.matches(QKeySequence.StandardKey.Undo):
                self.painter.undo()
                event.accept()
                return
            if event.matches(QKeySequence.StandardKey.Redo):
                self.painter.redo()
                event.accept()
                return

        super().keyPressEvent(event)
        QTimer.singleShot(0, lambda: self.mode.sync_geometry(self.painter))

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            self.mode.step_size(self.painter, 1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class PainterTextDragHandle(QWidget):
    """Small draggable handle used to reposition the active text draft."""

    SIZE = 16

    def __init__(self, painter, mode):
        super().__init__(painter)
        self.painter = painter
        self.mode = mode
        self._dragging = False
        self._dragStartGlobal = QPoint()
        self._dragStartOrigin = QPoint()
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.SizeAllCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing, True)
        qp.setPen(QPen(Qt.white, 2))
        qp.setBrush(QColor(Qt.black))
        qp.drawEllipse(self.rect().adjusted(2, 2, -2, -2))
        qp.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.mode.has_active():
            self._dragging = True
            self._dragStartGlobal = event.globalPosition().toPoint()
            self._dragStartOrigin = QPoint(self.mode.origin)
            self.grabMouse()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            delta = event.globalPosition().toPoint() - self._dragStartGlobal
            self.mode.drag(self.painter, self._dragStartOrigin, delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == Qt.LeftButton:
            self._dragging = False
            if self.mouseGrabber() is self:
                self.releaseMouse()
            if self.mode.editor is not None:
                self.mode.editor.setFocus(Qt.MouseFocusReason)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class TextDrawMode(BaseDrawMode):
    """
    Stateful Text-mode controller.

    Unlike vector/freehand handlers, Text mode owns a live QPlainTextEdit overlay
    until the draft is committed. The canvas only receives rasterized text at
    commit time, so the whole block remains one Painter undo action.
    """

    mode = DrawMode.TEXT
    HISTORY_KIND = "__painter_text_undo_kind__"

    def __init__(self, font_family: str = "Lato"):
        super().__init__()
        self.font_family = font_family
        self.editor = None
        self.drag_handle = None
        self.origin = QPoint()
        self.font_size = 3
        self.color = QColor(Qt.black)
        self.geometry_sync_pending = False
        self.from_undo = False

    # ---------- State / history metadata ----------

    def has_active(self) -> bool:
        return self.editor is not None

    def reopened_from_undo(self) -> bool:
        return self.editor is not None and self.from_undo

    def make_history_entry(self, widget, kind: str, state, draft: dict) -> dict:
        """Wrap a canvas snapshot with metadata used by two-stage Text undo."""
        return {
            self.HISTORY_KIND: kind,
            "state": state,
            "draft": {
                "text": str(draft.get("text", "")),
                "origin": QPoint(draft.get("origin", QPoint())),
                "font_size": max(1, int(draft.get("font_size", widget.brushSize))),
                "color": QColor(draft.get("color", widget.brushColor)),
            },
        }

    def history_kind(self, entry) -> str | None:
        if isinstance(entry, dict):
            return entry.get(self.HISTORY_KIND)
        return None

    # ---------- Lifecycle ----------

    def begin(self, widget, point: QPoint):
        """Start Text mode at a canvas point; release is intentionally a no-op."""
        self.start_edit(widget, point)

    def update(self, widget, point: QPoint):
        return

    def release(self, widget, point: QPoint):
        return

    def start_edit(
        self,
        widget,
        point: QPoint,
        text: str = "",
        font_size: int | None = None,
        color=None,
        from_undo: bool = False,
    ):
        """Start a live text draft without touching drawingLayer or history."""
        if self.editor is not None:
            return

        self.active = True
        self.origin = QPoint(point)
        self.font_size = max(1, int(widget.brushSize if font_size is None else font_size))
        self.color = QColor(widget.brushColor if color is None else color)
        self.from_undo = bool(from_undo)

        editor = PainterTextEdit(widget, self)
        editor.document().setDocumentMargin(0.0)
        self.editor = editor
        self.drag_handle = PainterTextDragHandle(widget, self)

        if text:
            editor.setPlainText(text)
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            editor.setTextCursor(cursor)

        self.sync_style(widget, refocus=False)
        self.sync_geometry(widget)
        editor.show()
        self.drag_handle.show()
        editor.raise_()
        self.drag_handle.raise_()
        editor.setFocus(Qt.MouseFocusReason)

    def restore_from_history(self, widget, draft: dict):
        """Restore a committed text block as a live editor for first-stage Undo."""
        font_size = max(1, int(draft.get("font_size", widget.brushSize)))
        color = QColor(draft.get("color", widget.brushColor))

        # Keep Painter controls aligned with the restored block.
        widget.brushSize = font_size
        widget._pen.setWidth(font_size)
        widget.brushColor = QColor(color)
        widget._pen.setColor(color)

        nodes = getattr(getattr(widget.window, "ui", None), "nodes", {}) or {}
        size_combo = nodes.get("painter.select.brush.size")
        if size_combo is not None:
            idx = size_combo.findText(str(font_size))
            if idx >= 0 and idx != size_combo.currentIndex():
                blocked = size_combo.blockSignals(True)
                size_combo.setCurrentIndex(idx)
                size_combo.blockSignals(blocked)

        color_combo = nodes.get("painter.select.brush.color")
        if color_combo is not None:
            for idx in range(color_combo.count()):
                data = color_combo.itemData(idx)
                try:
                    matches = QColor(data) == color
                except Exception:
                    matches = False
                if matches:
                    if idx != color_combo.currentIndex():
                        blocked = color_combo.blockSignals(True)
                        color_combo.setCurrentIndex(idx)
                        color_combo.blockSignals(blocked)
                    break

        self.start_edit(
            widget,
            QPoint(draft.get("origin", QPoint())),
            text=str(draft.get("text", "")),
            font_size=font_size,
            color=color,
            from_undo=True,
        )

    def cancel(self, widget, discard_undo_stage: bool = True):
        """Discard the complete live draft without creating an undo step."""
        editor = self.editor
        if editor is None:
            return

        was_from_undo = self.from_undo
        handle = self.drag_handle
        self._clear_overlay_refs()
        editor.hide()
        editor.deleteLater()
        if handle is not None:
            handle.hide()
            handle.deleteLater()

        # ESC/another operation at the intermediate Undo stage completes the
        # removal of the text action; do not leave a duplicate no-op stage.
        if (
            discard_undo_stage
            and was_from_undo
            and widget.undoStack
            and self.history_kind(widget.undoStack[-1]) == "text_draft_cancel"
        ):
            widget.undoStack.pop()

        widget.setFocus(Qt.OtherFocusReason)
        widget.update()

    def commit(self, widget) -> bool:
        """Rasterize the live draft onto drawingLayer as one undoable action."""
        editor = self.editor
        if editor is None:
            return False

        text = editor.toPlainText()
        origin = QPoint(self.origin)
        font_size = max(1, int(self.font_size))
        color = QColor(self.color)
        was_from_undo = self.from_undo

        # QPlainTextEdit renders glyphs inside its viewport (after QSS
        # border/padding). Commit from that actual viewport origin so the text
        # stays pixel-aligned with the live editor at every zoom level.
        viewport_pos = editor.viewport().mapTo(widget, QPoint(0, 0))
        zoom = max(0.0001, float(widget.zoom))
        draw_origin = QPoint(
            int(round(viewport_pos.x() / zoom)),
            int(round(viewport_pos.y() / zoom)),
        )

        handle = self.drag_handle
        self._clear_overlay_refs()
        editor.hide()
        editor.deleteLater()
        if handle is not None:
            handle.hide()
            handle.deleteLater()

        # Recommitting a block reopened by Undo replaces the intermediate stage
        # instead of introducing an extra undo level.
        if (
            was_from_undo
            and widget.undoStack
            and self.history_kind(widget.undoStack[-1]) == "text_draft_cancel"
        ):
            widget.undoStack.pop()

        if not text.strip():
            widget.setFocus(Qt.OtherFocusReason)
            widget.update()
            return False

        widget._ensure_layers()
        widget._ensure_composited_image()
        before = widget._snapshot_state()
        draft = {
            "text": text,
            "origin": QPoint(origin),
            "font_size": font_size,
            "color": QColor(color),
        }

        painter = QPainter(widget.drawingLayer)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setPen(QPen(color))
        font = QFont(self.font_family)
        font.setPixelSize(font_size)
        painter.setFont(font)

        metrics = QFontMetrics(font)
        baseline = draw_origin.y() + metrics.ascent()
        for line in text.split("\n"):
            painter.drawText(QPoint(draw_origin.x(), baseline), line.expandtabs(4))
            baseline += metrics.lineSpacing()
        painter.end()

        widget.undoStack.append(self.make_history_entry(widget, "text_commit", before, draft))
        widget.redoStack.clear()
        widget._mark_composite_dirty()
        widget.setFocus(Qt.OtherFocusReason)
        widget.update()
        return True

    def _clear_overlay_refs(self):
        self.editor = None
        self.drag_handle = None
        self.from_undo = False
        self.geometry_sync_pending = False
        self.active = False

    # ---------- Live editor formatting / geometry ----------

    def make_font(self, widget, display: bool = False) -> QFont:
        font = QFont(self.font_family)
        size = int(self.font_size)
        if display:
            size = int(round(size * widget.zoom))
        font.setPixelSize(max(1, size))
        return font

    def sync_style(self, widget, refocus: bool = False):
        """Apply current block font size/color to the whole draft and caret."""
        editor = self.editor
        if editor is None:
            return

        font = self.make_font(widget, display=True)
        editor.setFont(font)
        editor.document().setDefaultFont(font)
        color = QColor(self.color)

        cursor = editor.textCursor()
        cursor_pos = cursor.position()
        cursor_anchor = cursor.anchor()

        fmt = QTextCharFormat()
        fmt.setFont(font)
        fmt.setForeground(color)

        whole = QTextCursor(editor.document())
        whole.select(QTextCursor.SelectionType.Document)
        whole.mergeCharFormat(fmt)

        restored = QTextCursor(editor.document())
        restored.setPosition(cursor_anchor)
        restored.setPosition(cursor_pos, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(restored)
        editor.mergeCurrentCharFormat(fmt)
        editor.setCurrentCharFormat(fmt)

        display_px = max(1, font.pixelSize())
        editor.setCursorWidth(max(1, min(4, int(round(display_px / 18.0)))))

        palette = editor.palette()
        palette.setColor(QPalette.ColorRole.Text, color)
        palette.setColor(QPalette.ColorRole.Base, Qt.transparent)
        editor.setPalette(palette)
        editor.viewport().setPalette(palette)

        # App-wide stylesheets may override palette foreground in dark mode.
        editor.setStyleSheet(
            "QPlainTextEdit { "
            "background: transparent; "
            "border: 1px dashed rgba(128, 128, 128, 170); "
            "padding: 2px; "
            f"color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()}); "
            "}"
        )

        document = editor.document()
        document.markContentsDirty(0, document.characterCount())
        editor.viewport().update()
        self.sync_geometry(widget)
        self.schedule_geometry_sync(widget)
        if refocus:
            QTimer.singleShot(
                0,
                lambda e=editor: e.setFocus(Qt.OtherFocusReason) if e is self.editor else None,
            )

    def schedule_geometry_sync(self, widget):
        """Coalesce text/layout changes and auto-fit after QTextDocument relayout."""
        if self.editor is None or self.geometry_sync_pending:
            return
        self.geometry_sync_pending = True
        QTimer.singleShot(0, lambda: self._run_geometry_sync(widget))

    def _run_geometry_sync(self, widget):
        self.geometry_sync_pending = False
        self.sync_geometry(widget)
        editor = self.editor
        if editor is not None:
            editor.ensureCursorVisible()
            editor.viewport().update()

    def sync_geometry(self, widget):
        """Auto-fit the draft to current text, font size and zoom in real time."""
        editor = self.editor
        if editor is None:
            return

        font = self.make_font(widget, display=True)
        metrics = QFontMetrics(font)
        lines = editor.toPlainText().split("\n") or [""]

        widest = 0
        for line in lines:
            expanded = line.expandtabs(4)
            if expanded:
                bounds = metrics.boundingRect(expanded)
                widest = max(widest, metrics.horizontalAdvance(expanded), bounds.width())

        # QSS border/padding + glyph overhang + insertion caret safety margin.
        em = max(1, metrics.height())
        horizontal_extra = max(12, int(math.ceil(em * 0.45))) + editor.cursorWidth()
        vertical_extra = max(8, int(math.ceil(em * 0.35)))
        min_text_w = max(36, metrics.horizontalAdvance("MM") + horizontal_extra)

        desired_w = max(min_text_w, widest + horizontal_extra)
        line_count = max(1, len(lines))
        text_h = metrics.height() + (line_count - 1) * metrics.lineSpacing()
        desired_h = max(metrics.height() + vertical_extra, text_h + vertical_extra)

        x = int(round(self.origin.x() * widget.zoom))
        y = int(round(self.origin.y() * widget.zoom))
        x = max(0, min(max(0, widget.width() - 1), x))
        y = max(0, min(max(0, widget.height() - 1), y))

        available_w = max(1, widget.width() - x)
        available_h = max(1, widget.height() - y)
        width = min(desired_w, available_w)
        height = min(desired_h, available_h)
        geometry = QRect(x, y, width, height)
        if editor.geometry() != geometry:
            editor.setGeometry(geometry)
        editor.raise_()
        self.position_drag_handle(widget)

    def position_drag_handle(self, widget):
        editor = self.editor
        handle = self.drag_handle
        if editor is None or handle is None:
            return

        size = handle.width()
        x = editor.x() - size // 2
        y = editor.y() - size // 2
        x = max(0, min(max(0, widget.width() - size), x))
        y = max(0, min(max(0, widget.height() - size), y))
        handle.move(x, y)
        handle.raise_()

    def drag(self, widget, start_origin: QPoint, display_delta: QPoint):
        """Move the active text block without creating a separate undo step."""
        editor = self.editor
        if editor is None:
            return

        zoom = max(0.0001, float(widget.zoom))
        x = start_origin.x() + int(round(display_delta.x() / zoom))
        y = start_origin.y() + int(round(display_delta.y() / zoom))

        max_display_x = max(0, widget.width() - editor.width())
        max_display_y = max(0, widget.height() - editor.height())
        max_canvas_x = int(math.floor(max_display_x / zoom))
        max_canvas_y = int(math.floor(max_display_y / zoom))
        x = max(0, min(max_canvas_x, x))
        y = max(0, min(max_canvas_y, y))

        origin = QPoint(x, y)
        if origin != self.origin:
            self.origin = origin
            self.sync_geometry(widget)

    # ---------- Painter control integration ----------

    def step_size(self, widget, direction: int):
        common = getattr(getattr(widget.window, "controller", None), "painter", None)
        common = getattr(common, "common", None)
        if common is not None:
            common.step_brush_size(direction)

    def set_color(self, widget, color, refocus: bool = True):
        if self.editor is None:
            return
        self.color = QColor(color)
        self.sync_style(widget, refocus=refocus)

    def set_font_size(self, widget, size: int, refocus: bool = True):
        if self.editor is None:
            return
        self.font_size = max(1, int(size))
        self.sync_style(widget, refocus=refocus)

    def paste(self, widget) -> bool:
        if self.editor is None or not self.editor.hasFocus():
            return False
        self.editor.paste()
        self.sync_geometry(widget)
        return True

    def copy(self) -> bool:
        if self.editor is None or not self.editor.hasFocus():
            return False
        self.editor.copy()
        return True

    def delete_at_cursor(self, widget) -> bool:
        if self.editor is None or not self.editor.hasFocus():
            return False
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        else:
            cursor.deleteChar()
        self.editor.setTextCursor(cursor)
        self.sync_geometry(widget)
        return True
