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
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QStyledItemDelegate

class CalendarViewDelegate(QStyledItemDelegate):
    """Keep Qt's calendar delegate and add the current-weekday header background."""

    def __init__(self, calendar, base_delegate, parent=None):
        super().__init__(parent)
        self.calendar = calendar
        self.base_delegate = base_delegate

    def paint(self, painter, option, index):
        # Preserve the native/private QCalendarWidget rendering for every item.
        self.base_delegate.paint(painter, option, index)

        if not self.calendar.is_today_weekday_header(index):
            return

        color = self.calendar.get_hover_day_background_color()
        if not color.isValid() or color.alpha() == 0:
            return

        # QTextCharFormat background on weekday headers is not reliably painted
        # by QCalendarWidget (notably with stylesheets). Paint only this header
        # cell explicitly, then redraw its text so all other calendar rendering
        # remains untouched.
        painter.save()
        painter.fillRect(option.rect, color)

        font = QFont(option.font)
        if self.calendar.get_header_font_bold():
            font.setBold(True)
        painter.setFont(font)
        painter.setPen(option.palette.color(QPalette.ColorRole.Text))

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text is not None:
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, str(text))
        painter.restore()

    def sizeHint(self, option, index):
        return self.base_delegate.sizeHint(option, index)


