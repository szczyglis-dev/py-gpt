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

import math

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF
from PySide6.QtGui import QBrush, QPainter, QPen, QPolygonF

from .base import BaseDrawMode, DrawMode


class ShapeDrawMode(BaseDrawMode):
    """Base for drag-preview-commit shapes."""

    def update(self, widget, point: QPoint):
        if not self.active:
            return
        self.current = QPoint(point)
        widget.update()

    def release(self, widget, point: QPoint):
        if not self.active:
            return
        self.current = QPoint(point)
        if self.has_geometry():
            widget.document.ensure_layers()
            painter = QPainter(widget.document.drawing)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            self.draw_shape(widget, painter)
            painter.end()
            widget.document.mark_composite_dirty()
            widget._commit_draw_transaction()
        else:
            widget._cancel_draw_transaction()
        self.reset()
        widget.update()

    def cancel(self, widget):
        if not self.active:
            return
        # Shape previews have not touched drawingLayer yet, but cancel the
        # transaction uniformly so Free and shape modes share one lifecycle.
        widget._cancel_draw_transaction()
        self.reset()
        widget.update()

    def paint_preview(self, widget, painter):
        if self.active and self.has_geometry():
            painter.setRenderHint(QPainter.Antialiasing, True)
            self.draw_shape(widget, painter)

    def has_geometry(self) -> bool:
        return self.start != self.current

    @staticmethod
    def _outline_pen(widget) -> QPen:
        return QPen(widget.brushColor, widget.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def draw_shape(self, widget, painter: QPainter):
        raise NotImplementedError


class LineDrawMode(ShapeDrawMode):
    mode = DrawMode.LINE

    def draw_shape(self, widget, painter: QPainter):
        painter.setBrush(Qt.NoBrush)
        painter.setPen(self._outline_pen(widget))
        painter.drawLine(self.start, self.current)


class RectangleDrawMode(ShapeDrawMode):
    mode = DrawMode.RECTANGLE

    def draw_shape(self, widget, painter: QPainter):
        painter.setBrush(Qt.NoBrush)
        painter.setPen(self._outline_pen(widget))
        rect = QRectF(QPointF(self.start), QPointF(self.current)).normalized()
        painter.drawRect(rect)


class CircleDrawMode(ShapeDrawMode):
    mode = DrawMode.CIRCLE

    def draw_shape(self, widget, painter: QPainter):
        painter.setBrush(Qt.NoBrush)
        painter.setPen(self._outline_pen(widget))
        dx = float(self.current.x() - self.start.x())
        dy = float(self.current.y() - self.start.y())
        radius = math.hypot(dx, dy)
        if radius <= 0.0:
            return
        center = QPointF(self.start)
        rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2.0,
            radius * 2.0,
        )
        painter.drawEllipse(rect)


class ArrowDrawMode(ShapeDrawMode):
    mode = DrawMode.ARROW

    def draw_shape(self, widget, painter: QPainter):
        start = QPointF(self.start)
        tip = QPointF(self.current)
        dx = tip.x() - start.x()
        dy = tip.y() - start.y()
        length = math.hypot(dx, dy)
        if length <= 0.001:
            return

        ux = dx / length
        uy = dy / length
        px = -uy
        py = ux

        # Brush size controls both shaft thickness and the filled triangular head.
        desired_head_len = max(8.0, float(widget.brushSize) * 4.0)
        head_len = min(desired_head_len, max(1.0, length * 0.55))
        desired_half_width = max(4.0, float(widget.brushSize) * 2.0)
        half_width = min(desired_half_width, max(2.0, head_len * 0.72))

        base = QPointF(tip.x() - ux * head_len, tip.y() - uy * head_len)
        left = QPointF(base.x() + px * half_width, base.y() + py * half_width)
        right = QPointF(base.x() - px * half_width, base.y() - py * half_width)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(self._outline_pen(widget))
        painter.drawLine(start, base)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(widget.brushColor))
        painter.drawPolygon(QPolygonF([tip, left, right]))
