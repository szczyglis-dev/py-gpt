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
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QSizePolicy

CENTER_CALENDAR = True

class CalendarSquareHost(QWidget):
    """Keep the calendar square and responsive inside the Calendar tab."""

    def __init__(self, calendar: QWidget, parent=None):
        super().__init__(parent)
        self.calendar = calendar

        # Do not put the calendar in a layout here. A fixed-size child inside a
        # layout propagates its minimum size back to the host, which prevents
        # the host from shrinking when the application window gets smaller.
        # Keep it as a normal child and resize it from the host's resize event.
        self.calendar.setParent(self)
        self.calendar.setMinimumSize(0, 0)
        self.calendar.setMaximumSize(16777215, 16777215)
        self.calendar.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_calendar()

    def showEvent(self, event):
        super().showEvent(event)
        # The final host size may only be known after the tab/layout has been
        # shown, so fit once more on the next event-loop iteration.
        QTimer.singleShot(0, self._fit_calendar)

    def _fit_calendar(self) -> None:
        """Fit the largest possible square and optionally center it horizontally."""
        rect = self.contentsRect()
        side = min(rect.width(), rect.height())
        if side <= 0:
            return

        x = max(0, (rect.width() - side) // 2) if CENTER_CALENDAR else 0
        y = 0

        geometry = self.calendar.geometry()
        if (
            geometry.x() != x
            or geometry.y() != y
            or geometry.width() != side
            or geometry.height() != side
        ):
            self.calendar.setGeometry(x, y, side, side)


