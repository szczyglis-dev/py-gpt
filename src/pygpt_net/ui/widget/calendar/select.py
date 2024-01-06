#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 04:00:00                  #
# ================================================== #

from PySide6.QtCore import QRect, QDate
from PySide6.QtGui import QColor, QBrush, QFont, Qt
from PySide6.QtWidgets import QCalendarWidget


class CalendarSelect(QCalendarWidget):
    def __init__(self, window=None):
        """
        Calendar select widget

        :param window: main window
        """
        super(CalendarSelect, self).__init__(window)
        self.window = window
        self.currentYear = QDate.currentDate().year()
        self.currentMonth = QDate.currentDate().month()
        self.font_size = 9
        self.counters = {
            'ctx': {},  # num of ctx in date
        }
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)  # disable num of weeks display
        self.currentPageChanged.connect(self.page_changed)
        self.clicked[QDate].connect(self.on_day_clicked)

    def page_changed(self, year, month):
        """
        On page changed

        :param year: Year
        :param month: Month
        """
        self.currentYear = year
        self.currentMonth = month
        self.window.controller.calendar.on_page_changed(year, month)

    def paintCell(self, painter, rect, date: QDate):
        """
        On painting cell

        :param painter: Painter
        :param rect: Rectangle
        :param date: Date
        """
        super().paintCell(painter, rect, date)
        if date in self.counters['ctx']:
            padding = 2
            task_rect = QRect(rect.right() - padding - 20, rect.top() + padding, 20, 20)
            painter.save()
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawRect(task_rect)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont('Lato', self.font_size))
            painter.drawText(task_rect, Qt.AlignCenter, str(self.counters['ctx'][date]))
            painter.restore()

    def on_day_clicked(self, date: QDate):
        """
        On day clicked

        :param date: Date
        """
        year = date.year()
        month = date.month()
        day = date.day()
        self.window.controller.calendar.on_day_select(year, month, day)

    def add_ctx(self, date: QDate, num: int):
        """
        Add ctx counter to counters list

        :param date: Date
        :param num: Number of ctx
        """
        self.counters['ctx'][date] = str(num)
        self.updateCell(date)

    def update_ctx(self, tasks: dict):
        """
        Update ctx counters

        :param tasks: Tasks dict
        """
        self.counters['ctx'] = {QDate.fromString(date_str, 'yyyy-MM-dd'): count for date_str, count in tasks.items()}
        self.updateCells()
