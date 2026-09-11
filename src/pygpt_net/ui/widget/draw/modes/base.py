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

from enum import Enum

from PySide6.QtCore import QPoint


class DrawMode(str, Enum):
    """Stable IDs used by config and UI for Painter drawing modes."""

    FREE = "free"
    ARROW = "arrow"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    LINE = "line"

    @classmethod
    def from_value(cls, value):
        """Return a valid mode, falling back to Free."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except (TypeError, ValueError):
            return cls.FREE


DRAW_MODE_ORDER = (
    DrawMode.FREE,
    DrawMode.ARROW,
    DrawMode.RECTANGLE,
    DrawMode.CIRCLE,
    DrawMode.LINE,
)

DRAW_MODE_NAMES = {
    DrawMode.FREE: "Brush",
    DrawMode.ARROW: "Arrow",
    DrawMode.RECTANGLE: "Rectangle",
    DrawMode.CIRCLE: "Circle",
    DrawMode.LINE: "Line",
}

DRAW_MODE_TRANSLATION_KEYS = {
    DrawMode.FREE: "painter.draw.mode.free",
    DrawMode.ARROW: "painter.draw.mode.arrow",
    DrawMode.RECTANGLE: "painter.draw.mode.rectangle",
    DrawMode.CIRCLE: "painter.draw.mode.circle",
    DrawMode.LINE: "painter.draw.mode.line",
}


class BaseDrawMode:
    """Base class for a single Painter drawing gesture."""

    mode = DrawMode.FREE

    def __init__(self):
        self.active = False
        self.start = QPoint()
        self.current = QPoint()

    def begin(self, widget, point: QPoint):
        self.active = True
        self.start = QPoint(point)
        self.current = QPoint(point)
        widget._begin_draw_transaction()
        widget.drawing = True

    def update(self, widget, point: QPoint):
        if not self.active:
            return
        self.current = QPoint(point)

    def release(self, widget, point: QPoint):
        if not self.active:
            return
        self.current = QPoint(point)
        widget._commit_draw_transaction()
        self.reset()

    def cancel(self, widget):
        if not self.active:
            return
        widget._cancel_draw_transaction()
        self.reset()

    def paint_preview(self, widget, painter):
        """Paint transient shape preview. Free mode has no separate preview."""

    def reset(self):
        self.active = False
        self.start = QPoint()
        self.current = QPoint()
