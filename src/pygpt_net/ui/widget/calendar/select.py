#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

from typing import Tuple

from PySide6.QtCore import QRect, QDate
from PySide6.QtGui import QColor, QBrush, QFont, Qt, QAction, QContextMenuEvent, QIcon, QPixmap, QPen
from PySide6.QtWidgets import QCalendarWidget, QMenu

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class CalendarSelect(QCalendarWidget):
    def __init__(self, window=None):
        """
        Calendar select widget

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self.currentYear = QDate.currentDate().year()
        self.currentMonth = QDate.currentDate().month()
        self.currentDay = QDate.currentDate().day()
        self.font_size = 8
        self.counters = {
            'ctx': {},
            'notes': {},
        }
        self.labels = {}
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.currentPageChanged.connect(self.page_changed)
        self.clicked[QDate].connect(self.on_day_clicked)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)
        self.setProperty('class', 'calendar')
        self.tab = None
        self.installEventFilter(self)

        self._font_small = QFont('Lato', self.font_size)
        self._pen_today = QPen(QColor(0, 0, 0))
        self._pen_today.setWidth(2)
        self._pen_label = QPen(QColor(0, 0, 0))
        self._pen_label.setWidth(1)
        self._default_status_bg = QColor(100, 100, 100)
        self._default_status_font = QColor(255, 255, 255)
        self._theme_cached = None
        self._counter_bg = QColor(240, 240, 240)
        self._counter_font = QColor(0, 0, 0)
        self._today = QDate.currentDate()
        self._update_theme_cache()

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)

    def page_changed(self, year, month):
        """
        On page changed

        :param year: Year
        :param month: Month
        """
        self.currentYear = year
        self.currentMonth = month
        self.window.controller.calendar.on_page_changed(year, month)

    def _update_theme_cache(self):
        theme = self.window.core.config.get("theme")
        if theme != self._theme_cached:
            self._theme_cached = theme
            if isinstance(theme, str) and theme.startswith('dark'):
                self._counter_bg = QColor(40, 40, 40)
                self._counter_font = QColor(255, 255, 255)
            else:
                self._counter_bg = QColor(240, 240, 240)
                self._counter_font = QColor(0, 0, 0)

    def paintCell(self, painter, rect, date: QDate):
        """
        On painting cell

        :param painter: Painter
        :param rect: Rectangle
        :param date: Date
        """
        self._update_theme_cache()
        cd = QDate.currentDate()
        if cd != self._today:
            self._today = cd

        super().paintCell(painter, rect, date)

        if date == self._today:
            painter.save()
            painter.setPen(self._pen_today)
            painter.drawRect(rect)
            painter.restore()

        ctx_count = self.counters['ctx'].get(date)
        if ctx_count is not None:
            padding = 2
            task_rect = QRect(
                rect.right() - padding - 20,
                rect.top() + padding,
                20,
                20,
            )
            painter.save()
            painter.fillRect(task_rect, self._counter_bg)
            painter.setPen(self._counter_font)
            painter.setFont(self._font_small)
            painter.drawText(
                task_rect,
                Qt.AlignCenter,
                str(ctx_count),
            )
            painter.restore()

        notes = self.counters['notes'].get(date)
        if notes:
            colors_map = self.window.controller.ui.get_colors()
            padding = 2
            task_rect = QRect(
                rect.left() + padding,
                rect.bottom() - padding - 20,
                20,
                20,
            )
            painter.save()
            for status, count in notes.items():
                info = colors_map.get(status)
                if info:
                    bg_color, font_color = info['color'], info['font']
                else:
                    bg_color, font_color = self._default_status_bg, self._default_status_font
                painter.fillRect(task_rect, bg_color)
                painter.setPen(font_color)
                painter.setFont(self._font_small)
                painter.drawText(
                    task_rect,
                    Qt.AlignCenter,
                    "!",
                )
            painter.restore()

        day_labels = self.labels.get(date)
        if day_labels:
            colors_map = self.window.controller.ui.get_colors()
            painter.save()
            painter.setPen(self._pen_label)
            prev_left = rect.left()
            top = rect.top() + 2
            x = prev_left + 2
            for label_id in day_labels:
                info = colors_map.get(label_id)
                if not info:
                    continue
                color = info['color']
                painter.setBrush(QBrush(color))
                painter.drawRect(
                    x,
                    top,
                    5,
                    5,
                )
                x += 7
            painter.restore()

    def get_color_for_status(self, status: int) -> Tuple[QColor, QColor]:
        """
        Get color for status

        :param status: status
        :return: color, font color
        """
        colors = self.window.controller.ui.get_colors()
        info = colors.get(status)
        if info:
            return info['color'], info['font']
        return self._default_status_bg, self._default_status_font

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
        self.window.controller.calendar.on_ctx_select(year, month, day)

        if self.tab is not None:
            col_idx = self.tab.column_idx
            self.window.controller.ui.tabs.on_column_focus(col_idx)

    def add_ctx(self, date: QDate, num: int):
        """
        Add ctx counter to counter list

        :param date: date
        :param num: number of ctx
        """
        self.counters['ctx'][date] = str(num)
        self.updateCell(date)

    def update_ctx(self, counters: dict, labels: dict):
        """
        Update ctx counters

        :param counters: counters dict
        :param labels: labels dict
        """
        self.counters['ctx'] = {
            QDate.fromString(date_str, 'yyyy-MM-dd'): count for date_str, count in counters.items()
        }
        self.labels = {
            QDate.fromString(date_str, 'yyyy-MM-dd'): lab for date_str, lab in labels.items()
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
                lambda checked=False, s_id=status_id, date=selected_date: self.set_label_for_day(date, s_id)
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