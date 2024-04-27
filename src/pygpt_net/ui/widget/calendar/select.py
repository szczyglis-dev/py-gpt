#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.27 10:00:00                  #
# ================================================== #

from PySide6.QtCore import QRect, QDate
from PySide6.QtGui import QColor, QBrush, QFont, Qt, QAction, QContextMenuEvent, QIcon, QPixmap, QPen
from PySide6.QtWidgets import QCalendarWidget, QMenu

from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        self.currentDay = QDate.currentDate().day()
        self.font_size = 9
        self.counters = {
            'ctx': {},  # num of ctx in date
            'notes': {},  # num of notes in date
        }
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)  # disable num of weeks display
        self.currentPageChanged.connect(self.page_changed)
        self.clicked[QDate].connect(self.on_day_clicked)

        # context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)
        self.setProperty('class', 'calendar')

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

        # current date
        if date == QDate.currentDate():
            painter.save()
            pen = QPen(QColor(0, 0, 0))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(rect)
            painter.restore()

        # ctx counter
        if date in self.counters['ctx']:
            padding = 2
            task_rect = QRect(
                rect.right() - padding - 20,
                rect.top() + padding,
                20,
                20,
            )
            painter.save()
            painter.setBrush(QBrush(QColor(40, 40, 40)))
            painter.drawRect(task_rect)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont('Lato', self.font_size))
            painter.drawText(
                task_rect,
                Qt.AlignCenter,
                str(self.counters['ctx'][date]),
            )
            painter.restore()

        # notes counter
        if date in self.counters['notes']:
            day_notes = self.counters['notes'][date]
            for status, count in day_notes.items():
                padding = 2
                task_rect = QRect(
                    rect.left() + padding,
                    rect.bottom() - padding - 20,
                    20,
                    20,
                )
                painter.save()
                bg_color, font_color = self.get_color_for_status(status)
                painter.setBrush(QBrush(bg_color))
                painter.drawRect(task_rect)
                painter.setPen(font_color)
                painter.setFont(QFont('Lato', self.font_size))
                painter.drawText(
                    task_rect,
                    Qt.AlignCenter,
                    "!",
                )  # str(count)
                painter.restore()

    def get_color_for_status(self, status: int) -> (QColor, QColor):
        """
        Get color for status

        :param status: status
        :return: color, font color
        """
        colors = self.window.controller.ui.get_colors()
        if status in colors:
            return colors[status]['color'], colors[status]['font']
        else:
            return QColor(100, 100, 100), QColor(255, 255, 255)

    def on_day_clicked(self, date: QDate):
        """
        On day clicked

        :param date: Date
        """
        year = date.year()
        month = date.month()
        day = date.day()
        self.currentYear = year
        self.currentMonth = month
        self.currentDay = day
        self.window.controller.calendar.on_day_select(year, month, day)

        # check if date has ctx TODO: think about better solution
        # if date in self.counters['ctx']:
        self.window.controller.calendar.on_ctx_select(year, month, day)

    def add_ctx(self, date: QDate, num: int):
        """
        Add ctx counter to counter list

        :param date: date
        :param num: number of ctx
        """
        self.counters['ctx'][date] = str(num)
        self.updateCell(date)

    def update_ctx(self, counters: dict):
        """
        Update ctx counters

        :param counters: counters dict
        """
        self.counters['ctx'] = {
            QDate.fromString(date_str, 'yyyy-MM-dd'): count for date_str, count in counters.items()
        }
        self.updateCells()

    def update_notes(self, counters: dict):
        """
        Update notes counters

        :param counters: counters dict
        """
        self.counters['notes'] = {
            QDate.fromString(date_str, 'yyyy-MM-dd'): count for date_str, count in counters.items()
        }
        self.updateCells()

    def open_context_menu(self, position):
        """
        Open context menu

        :param position: position
        """
        colors = self.window.controller.ui.get_colors()
        selected_date = self.selectedDate()
        context_menu = QMenu(self)
        action_text = trans('calendar.day.search') + ': ' + selected_date.toString()
        action = QAction(action_text, self)
        action.setIcon(QIcon(":/icons/history.svg"))
        action.triggered.connect(lambda: self.execute_action(selected_date))
        context_menu.addAction(action)
        
        # set label menu
        set_label_menu = context_menu.addMenu(trans('calendar.day.label'))
        for status_id, status_info in colors.items():
            name = trans('calendar.day.' + status_info['label'])
            if status_id == 0:
                name = '-'
            color = status_info['color']
            pixmap = QPixmap(16, 16)
            pixmap.fill(color)
            icon = QIcon(pixmap)
            status_action = QAction(icon, name, self)
            status_action.triggered.connect(
                lambda checked=False, s_id=status_id: self.set_label_for_day(selected_date, s_id)
            )
            set_label_menu.addAction(status_action)

        context_menu.exec(self.mapToGlobal(position))

    def execute_action(self, date):
        """
        On select date from context menu

        :param date: QDate
        """
        year = date.year()
        month = date.month()
        day = date.day()
        self.window.controller.calendar.on_ctx_select(
            year,
            month,
            day,
        )

    def contextMenuEvent(self, event: QContextMenuEvent):
        """
        On context menu event

        :param event: context menu event
        """
        self.open_context_menu(event.pos())

    def set_label_for_day(self, date: QDate, status_id: int):
        """
        Set label for day

        :param date: date
        :param status_id: status id
        """
        self.window.controller.calendar.note.update_status(
            status_id,
            date.year(),
            date.month(),
            date.day(),
        )

