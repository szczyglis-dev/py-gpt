#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.03 20:31:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QPen

from .base import BaseDrawMode, DrawMode


class FreeDrawMode(BaseDrawMode):
    """Classic freehand brush. Also used by the eraser for every draw mode."""

    mode = DrawMode.FREE

    def _setup_painter(self, widget) -> QPainter:
        painter = QPainter(widget.document.drawing)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if widget._mode == "erase":
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(QPen(Qt.transparent, widget.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(widget._pen)
        return painter

    def begin(self, widget, point: QPoint):
        super().begin(widget, point)
        widget.document.ensure_layers()
        painter = self._setup_painter(widget)
        painter.drawPoint(point)
        painter.end()
        widget.document.mark_composite_dirty()
        dirty = widget._dirty_canvas_rect_for_point(point, widget.brushSize)
        widget.update(widget.viewport.from_canvas_rect(dirty))

    def update(self, widget, point: QPoint):
        if not self.active:
            return
        widget.document.ensure_layers()
        previous = QPoint(self.current)
        self.current = QPoint(point)
        painter = self._setup_painter(widget)
        painter.drawLine(previous, self.current)
        painter.end()
        widget.document.mark_composite_dirty()
        dirty = widget._dirty_canvas_rect_for_segment(previous, self.current, widget.brushSize)
        widget.update(widget.viewport.from_canvas_rect(dirty))

    def release(self, widget, point: QPoint):
        if not self.active:
            return
        # Preserve a final segment even if Qt did not emit a last move event.
        if point != self.current:
            self.update(widget, point)
        widget._commit_draw_transaction()
        self.reset()
