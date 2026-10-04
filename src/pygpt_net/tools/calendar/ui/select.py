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

from typing import Tuple

from PySide6.QtCore import QRect, QDate, Property, QEvent
from PySide6.QtGui import QColor, QBrush, QFont, Qt, QAction, QContextMenuEvent, QCursor, QIcon, QPixmap, QPen, QPalette
from PySide6.QtWidgets import QAbstractItemView, QCalendarWidget, QMenu, QStyledItemDelegate, QToolTip, QWidget

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


from .delegate import CalendarViewDelegate


class CalendarSelect(QCalendarWidget):
    def __init__(self, session):
        """
        Calendar select widget

        :param window: main window
        """
        super().__init__()
        self.session = session
        self.window = session.window
        self._today_background_color = QColor()
        self._today_text_color = QColor()
        self._today_font_bold = False
        self._inactive_day_background_color = QColor()
        self._inactive_day_text_color = QColor()
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
        self._cell_rects = {}
        self._note_marker_rects = {}
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
        self._default_status_bg = QColor(100, 100, 100)
        self._default_status_font = QColor(255, 255, 255)
        self._today = QDate.currentDate()
        self._sync_today_weekday_header()
        self._move_navigation_bar_to_bottom()

    def _move_navigation_bar_to_bottom(self):
        """Move Qt's month/year navigation row below the calendar grid."""
        nav = self.findChild(QWidget, "qt_calendar_navigationbar")
        if nav is None:
            return
        parent = nav.parentWidget()
        layout = parent.layout() if parent is not None else self.layout()
        if layout is None or layout.indexOf(nav) < 0:
            return
        layout.removeWidget(nav)
        layout.addWidget(nav)

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

    def get_inactive_day_text_color(self):
        return self._inactive_day_text_color

    def set_inactive_day_text_color(self, color):
        self._inactive_day_text_color = QColor(color)
        self.updateCells()

    inactiveDayTextColor = Property(
        QColor,
        get_inactive_day_text_color,
        set_inactive_day_text_color,
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
        Focus, hover, tooltip and day-note click handling.

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.tabs.on_column_focus(col_idx)

        if self._calendar_view is not None and source is self._calendar_view.viewport():
            event_type = event.type()

            if event_type in (QEvent.Type.MouseMove, QEvent.Type.Enter, QEvent.Type.Leave):
                self.updateCells()

            if event_type == QEvent.Type.ToolTip:
                try:
                    pos = event.position().toPoint()
                except AttributeError:
                    pos = event.pos()
                date = self._date_at_viewport_pos(pos)
                if date is not None and self.counters['notes'].get(date):
                    preview = self.session.note.get_preview(
                        date.year(),
                        date.month(),
                        date.day(),
                        30,
                    )
                    if preview:
                        try:
                            global_pos = event.globalPosition().toPoint()
                        except AttributeError:
                            global_pos = event.globalPos()
                        text = preview
                        QToolTip.showText(
                            global_pos,
                            text,
                            self._calendar_view.viewport(),
                            self._cell_rects.get(date, QRect()),
                        )
                        return True
                QToolTip.hideText()
                return True

            if event_type == QEvent.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                try:
                    pos = event.position().toPoint()
                except AttributeError:
                    pos = event.pos()
                date = self._date_at_viewport_pos(pos)
                if date is not None:
                    popup = self.session.widgets.get('note.popup')
                    marker_rect = self._note_marker_rects.get(date)
                    marker_clicked = marker_rect is not None and marker_rect.contains(pos)

                    # A click on the note marker opens the editor.  While the
                    # popup is open, clicking any calendar cell switches it to
                    # that day; clicking the same day toggles it closed.
                    if marker_clicked or (popup is not None and popup.isVisible()):
                        self.setSelectedDate(date)
                        self.currentYear = date.year()
                        self.currentMonth = date.month()
                        self.currentDay = date.day()
                        self.session.toggle_note_popup(
                            date.year(),
                            date.month(),
                            date.day(),
                            self.get_cell_global_rect(date.year(), date.month(), date.day()),
                        )
                        if self.tab is not None:
                            self.window.controller.tabs.on_column_focus(self.tab.column_idx)
                        return True

        return super().eventFilter(source, event)

    def _date_at_viewport_pos(self, pos):
        """Return the painted date cell under a viewport position."""
        for date, rect in self._cell_rects.items():
            if rect.contains(pos):
                return date
        return None

    def get_cell_global_rect(self, year: int, month: int, day: int) -> QRect:
        """Return a visible day-cell rectangle in global coordinates."""
        if self._calendar_view is None:
            return QRect()
        date = QDate(year, month, day)
        rect = self._cell_rects.get(date)
        if rect is None or not rect.isValid():
            return QRect()
        top_left = self._calendar_view.viewport().mapToGlobal(rect.topLeft())
        return QRect(top_left, rect.size())

    def page_changed(self, year, month):
        """
        On page changed

        :param year: Year
        :param month: Month
        """
        self.currentYear = year
        self.currentMonth = month
        self._cell_rects.clear()
        self._note_marker_rects.clear()
        self.session.on_page_changed(year, month)

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

        self._cell_rects[date] = QRect(rect)
        self._note_marker_rects.pop(date, None)

        super().paintCell(painter, rect, date)

        is_inactive = date.year() != self.currentYear or date.month() != self.currentMonth
        if is_inactive:
            painter.save()
            if (
                self._inactive_day_background_color.isValid()
                and self._inactive_day_background_color.alpha() > 0
            ):
                painter.fillRect(rect, self._inactive_day_background_color)
            if self._inactive_day_text_color.isValid():
                painter.setPen(self._inactive_day_text_color)
            else:
                painter.setPen(self.palette().color(QPalette.Disabled, QPalette.Text))
            painter.drawText(rect, Qt.AlignCenter, str(date.day()))
            painter.restore()

        # Keep the selected-day background consistent with hover.
        # Today keeps its dedicated styling.
        if (
            date == self.selectedDate()
            and date != self._today
            and self._hover_day_background_color.isValid()
        ):
            painter.save()
            painter.fillRect(rect, self._hover_day_background_color)
            if is_inactive:
                if self._inactive_day_text_color.isValid():
                    painter.setPen(self._inactive_day_text_color)
                else:
                    painter.setPen(self.palette().color(QPalette.Disabled, QPalette.Text))
            else:
                painter.setPen(self.palette().color(QPalette.Active, QPalette.Text))
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
                    if self._inactive_day_text_color.isValid():
                        painter.setPen(self._inactive_day_text_color)
                    else:
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
            self._note_marker_rects[date] = QRect(task_rect)
            painter.save()
            for status, count in notes.items():
                info = colors_map.get(status)
                if info:
                    bg_color = info['color']
                else:
                    bg_color = self._default_status_bg
                painter.fillRect(task_rect, bg_color)
            painter.restore()

        day_labels = self.labels.get(date)
        if day_labels:
            colors_map = self.window.controller.ui.get_colors()
            painter.save()
            painter.setPen(Qt.NoPen)
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
        self.session.on_day_select(year, month, day)

        if self.tab is not None:
            col_idx = self.tab.column_idx
            self.window.controller.tabs.on_column_focus(col_idx)

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
        global_pos = self.mapToGlobal(position)
        selected_date = self.selectedDate()

        if self._calendar_view is not None:
            viewport_pos = self._calendar_view.viewport().mapFromGlobal(global_pos)
            date_at_pos = self._date_at_viewport_pos(viewport_pos)
            if date_at_pos is not None:
                selected_date = date_at_pos
                self.setSelectedDate(selected_date)

        context_menu = QMenu(self)

        note_action = QAction(QIcon(":/icons/edit.svg"), trans('calendar.note.edit'), self)
        note_action.triggered.connect(
            lambda checked=False, date=selected_date: self.session.toggle_note_popup(
                date.year(),
                date.month(),
                date.day(),
                self.get_cell_global_rect(date.year(), date.month(), date.day()),
            )
        )
        context_menu.addAction(note_action)
        context_menu.addSeparator()

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

        context_menu.exec(global_pos)

    def execute_action(self, date):
        """
        On select date from context menu

        :param date: QDate
        """
        year = date.year()
        month = date.month()
        day = date.day()
        self.session.on_ctx_select(
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
        self.session.note.update_status(
            status_id,
            date.year(),
            date.month(),
            date.day(),
        )