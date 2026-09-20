#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 23:00:00                  #
# ================================================== #

from typing import Tuple

from PySide6.QtCore import QRect, QDate, Property, QEvent
from PySide6.QtGui import QColor, QBrush, QFont, Qt, QAction, QContextMenuEvent, QCursor, QIcon, QPixmap, QPen, QPalette
from PySide6.QtWidgets import QAbstractItemView, QCalendarWidget, QMenu, QStyledItemDelegate

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


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


class CalendarSelect(QCalendarWidget):
    def __init__(self, window=None):
        """
        Calendar select widget

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self._today_background_color = QColor()
        self._today_text_color = QColor()
        self._today_font_bold = False
        self._inactive_day_background_color = QColor()
        self._day_border_color = QColor()
        self._counter_background_color = QColor()
        self._counter_text_color = QColor()
        self._header_background_color = QColor()
        self._header_font_bold = False
        self._hover_day_background_color = QColor()
        self._hover_today_background_color = QColor()
        self._hover_today_text_color = QColor()
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

        self._calendar_view = self.findChild(QAbstractItemView, 'qt_calendar_calendarview')
        self._calendar_base_delegate = None
        self._calendar_delegate = None
        if self._calendar_view is not None:
            self._calendar_view.viewport().setMouseTracking(True)
            self._calendar_view.viewport().installEventFilter(self)
            self._calendar_base_delegate = self._calendar_view.itemDelegate()
            self._calendar_delegate = CalendarViewDelegate(
                self,
                self._calendar_base_delegate,
                self._calendar_view,
            )
            self._calendar_view.setItemDelegate(self._calendar_delegate)

        self._font_small = QFont('Lato', self.font_size)
        self._pen_label = QPen(QColor(0, 0, 0))
        self._pen_label.setWidth(1)
        self._default_status_bg = QColor(100, 100, 100)
        self._default_status_font = QColor(255, 255, 255)
        self._today = QDate.currentDate()
        self._sync_today_weekday_header()

    @staticmethod
    def _enum_value(value):
        """Return an int for Qt enum values across supported PySide6 versions."""
        if hasattr(value, 'value'):
            return int(value.value)
        return int(value)

    def is_today_weekday_header(self, index) -> bool:
        """Return True for the weekday-header cell matching the current day."""
        if index is None or not index.isValid() or index.row() != 0:
            return False
        if self.horizontalHeaderFormat() == QCalendarWidget.NoHorizontalHeader:
            return False

        first_day = self._enum_value(self.firstDayOfWeek())
        today_weekday = QDate.currentDate().dayOfWeek()
        today_column = (today_weekday - first_day) % 7
        return index.column() == today_column

    def _sync_today_weekday_header(self):
        """Refresh the current weekday header highlight."""
        self._today = QDate.currentDate()
        if self._calendar_view is not None:
            self._calendar_view.viewport().update()

    def get_today_background_color(self):
        return self._today_background_color

    def set_today_background_color(self, color):
        self._today_background_color = QColor(color)
        self.updateCells()

    todayBackgroundColor = Property(QColor, get_today_background_color, set_today_background_color)

    def get_today_text_color(self):
        return self._today_text_color

    def set_today_text_color(self, color):
        self._today_text_color = QColor(color)
        self.updateCells()

    todayTextColor = Property(QColor, get_today_text_color, set_today_text_color)

    def get_today_font_bold(self):
        return self._today_font_bold

    def set_today_font_bold(self, value):
        self._today_font_bold = bool(value)
        self.updateCells()

    todayFontBold = Property(bool, get_today_font_bold, set_today_font_bold)

    def get_inactive_day_background_color(self):
        return self._inactive_day_background_color

    def set_inactive_day_background_color(self, color):
        self._inactive_day_background_color = QColor(color)
        self.updateCells()

    inactiveDayBackgroundColor = Property(
        QColor,
        get_inactive_day_background_color,
        set_inactive_day_background_color,
    )

    def get_day_border_color(self):
        return self._day_border_color

    def set_day_border_color(self, color):
        self._day_border_color = QColor(color)
        self.updateCells()

    dayBorderColor = Property(QColor, get_day_border_color, set_day_border_color)

    def get_counter_background_color(self):
        return self._counter_background_color

    def set_counter_background_color(self, color):
        self._counter_background_color = QColor(color)
        self.updateCells()

    counterBackgroundColor = Property(
        QColor,
        get_counter_background_color,
        set_counter_background_color,
    )

    def get_counter_text_color(self):
        return self._counter_text_color

    def set_counter_text_color(self, color):
        self._counter_text_color = QColor(color)
        self.updateCells()

    counterTextColor = Property(QColor, get_counter_text_color, set_counter_text_color)

    def get_header_background_color(self):
        return self._header_background_color

    def set_header_background_color(self, color):
        self._header_background_color = QColor(color)
        fmt = self.headerTextFormat()
        if self._header_background_color.isValid():
            fmt.setBackground(QBrush(self._header_background_color))
        else:
            fmt.clearBackground()
        self.setHeaderTextFormat(fmt)
        self._sync_today_weekday_header()

    headerBackgroundColor = Property(
        QColor,
        get_header_background_color,
        set_header_background_color,
    )

    def get_header_font_bold(self):
        return self._header_font_bold

    def set_header_font_bold(self, value):
        self._header_font_bold = bool(value)
        fmt = self.headerTextFormat()
        fmt.setFontWeight(
            QFont.Weight.Bold if self._header_font_bold else QFont.Weight.Normal
        )
        self.setHeaderTextFormat(fmt)
        self._sync_today_weekday_header()

    headerFontBold = Property(bool, get_header_font_bold, set_header_font_bold)

    def get_hover_day_background_color(self):
        return self._hover_day_background_color

    def set_hover_day_background_color(self, color):
        self._hover_day_background_color = QColor(color)
        self._sync_today_weekday_header()
        self.updateCells()

    hoverDayBackgroundColor = Property(
        QColor,
        get_hover_day_background_color,
        set_hover_day_background_color,
    )

    def get_hover_today_background_color(self):
        return self._hover_today_background_color

    def set_hover_today_background_color(self, color):
        self._hover_today_background_color = QColor(color)
        self.updateCells()

    hoverTodayBackgroundColor = Property(
        QColor,
        get_hover_today_background_color,
        set_hover_today_background_color,
    )

    def get_hover_today_text_color(self):
        return self._hover_today_text_color

    def set_hover_today_text_color(self, color):
        self._hover_today_text_color = QColor(color)
        self.updateCells()

    hoverTodayTextColor = Property(
        QColor,
        get_hover_today_text_color,
        set_hover_today_text_color,
    )

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

        if (
            self._calendar_view is not None
            and source is self._calendar_view.viewport()
            and event.type() in (QEvent.Type.MouseMove, QEvent.Type.Enter, QEvent.Type.Leave)
        ):
            self.updateCells()

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

    def paintCell(self, painter, rect, date: QDate):
        """
        On painting cell

        :param painter: Painter
        :param rect: Rectangle
        :param date: Date
        """
        cd = QDate.currentDate()
        if cd != self._today:
            self._today = cd
            self._sync_today_weekday_header()

        super().paintCell(painter, rect, date)

        is_inactive = date.year() != self.currentYear or date.month() != self.currentMonth
        if (
            is_inactive
            and self._inactive_day_background_color.isValid()
            and self._inactive_day_background_color.alpha() > 0
        ):
            painter.save()
            painter.fillRect(rect, self._inactive_day_background_color)
            painter.setPen(self.palette().color(QPalette.Disabled, QPalette.Text))
            painter.drawText(rect, Qt.AlignCenter, str(date.day()))
            painter.restore()

        if date == self._today:
            painter.save()
            if self._today_background_color.isValid():
                painter.fillRect(rect, self._today_background_color)
            if self._today_text_color.isValid():
                painter.setPen(self._today_text_color)
            if self._today_font_bold:
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, str(date.day()))
            painter.restore()

        if (
            self._calendar_view is not None
            and self._hover_day_background_color.isValid()
            and self._calendar_view.viewport().underMouse()
        ):
            cursor_pos = self._calendar_view.viewport().mapFromGlobal(QCursor.pos())
            if rect.contains(cursor_pos):
                painter.save()
                hover_background = self._hover_day_background_color
                if date == self._today and self._hover_today_background_color.isValid():
                    hover_background = self._hover_today_background_color
                painter.fillRect(rect, hover_background)
                if date == self._today:
                    if self._hover_today_text_color.isValid():
                        painter.setPen(self._hover_today_text_color)
                    elif self._today_text_color.isValid():
                        painter.setPen(self._today_text_color)
                    if self._today_font_bold:
                        font = painter.font()
                        font.setBold(True)
                        painter.setFont(font)
                elif is_inactive:
                    painter.setPen(self.palette().color(QPalette.Disabled, QPalette.Text))
                else:
                    painter.setPen(self.palette().color(QPalette.Active, QPalette.Text))
                painter.drawText(rect, Qt.AlignCenter, str(date.day()))
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
            if self._counter_background_color.isValid():
                painter.fillRect(task_rect, self._counter_background_color)
            if self._counter_text_color.isValid():
                painter.setPen(self._counter_text_color)
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

        if self._day_border_color.isValid():
            painter.save()
            painter.setPen(QPen(self._day_border_color, 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
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