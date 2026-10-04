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

from PySide6.QtCore import Qt, QDate, QLocale, QRect, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizeGrip,
    QToolButton,
    QVBoxLayout,
)

from pygpt_net.utils import trans


class CalendarNoteHeader(QFrame):
    """Draggable header used by the floating day-note editor."""

    def __init__(self, popup=None):
        super().__init__(popup)
        self.popup = popup
        self._drag_offset = None
        self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.popup is not None:
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self.popup.frameGeometry().topLeft()
            )
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_offset is not None
            and self.popup is not None
            and event.buttons() & Qt.LeftButton
        ):
            self.popup.move(
                event.globalPosition().toPoint() - self._drag_offset
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class CalendarNotePopup(QFrame):
    """Resizable floating editor for a calendar day note."""

    DEFAULT_WIDTH = 420
    DEFAULT_HEIGHT = 260
    MARGIN = 8

    def __init__(self, window=None, editor=None, parent=None):
        super().__init__(parent or window, Qt.Tool | Qt.FramelessWindowHint)
        self.window = window
        self.editor = editor
        self.current_date = None

        self.setProperty("class", "calendar-note-popup")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumSize(300, 180)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

        self.header_bar = CalendarNoteHeader(self)
        self.header = QLabel(self.header_bar)
        self.header.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        header_font = QFont(self.header.font())
        header_font.setBold(True)
        self.header.setFont(header_font)

        self.close_button = QToolButton(self.header_bar)
        self.close_button.setAutoRaise(True)
        # Use the resource directly in QSS as well as QIcon.  The explicit
        # image rule avoids platform/style-specific QToolButton icon painting
        # issues (notably on some dark themes).
        self.close_button.setIcon(QIcon(":/icons/close.svg"))
        self.close_button.setIconSize(QSize(18, 18))
        self.close_button.setFixedSize(26, 26)
        self.close_button.setStyleSheet(
            "QToolButton {"
            "  border: 0;"
            "  background: transparent;"
            "  padding: 4px;"
            "  image: url(:/icons/close.svg);"
            "}"
            "QToolButton:hover {"
            "  background: rgba(127, 127, 127, 38);"
            "}"
        )
        self.close_button.setCursor(Qt.ArrowCursor)
        self.close_button.clicked.connect(self.hide)

        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(6, 4, 2, 0)
        header_layout.setSpacing(4)
        header_layout.addWidget(self.header)
        header_layout.addStretch(1)
        header_layout.addWidget(self.close_button)

        self.grip = QSizeGrip(self)
        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 2, 2)
        grip_layout.addStretch(1)
        grip_layout.addWidget(self.grip, 0, Qt.AlignRight | Qt.AlignBottom)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(2)
        layout.addWidget(self.header_bar)
        if self.editor is not None:
            layout.addWidget(self.editor, 1)
        layout.addLayout(grip_layout)

        self.refresh_translation()
        self.hide()

    def _weekday_name(self, date: QDate) -> str:
        """Return the full weekday name using the active application language."""
        try:
            lang = self.window.core.config.get_lang() if self.window is not None else "en"
            weekday = QLocale(lang).dayName(
                date.dayOfWeek(),
                QLocale.FormatType.LongFormat,
            ).strip().rstrip(".")
            if weekday:
                return weekday
        except Exception:
            pass
        return date.toString("dddd")

    def _date_label(self, year: int, month: int, day: int) -> str:
        """Build the localized date label shown in the popup header."""
        target = QDate(year, month, day)
        if not target.isValid():
            return f"{year:04d}-{month:02d}-{day:02d}"

        today = QDate.currentDate()
        delta = today.daysTo(target)
        weekday = self._weekday_name(target)

        if delta == 0:
            return trans("dt.today")
        if delta == -1:
            return f"{trans('dt.yesterday')}, {weekday}" if weekday else trans("dt.yesterday")
        if delta == 1:
            return f"{trans('dt.tomorrow')}, {weekday}" if weekday else trans("dt.tomorrow")
        if delta == 2:
            value = trans("dt.day_after_tomorrow")
            return f"{value}, {weekday}" if weekday else value

        date_text = target.toString("yyyy-MM-dd")
        return f"{weekday}, {date_text}" if weekday else date_text

    def refresh_translation(self):
        """Refresh translated labels."""
        title = trans("calendar.note.label")
        if self.current_date is not None:
            year, month, day = self.current_date
            title += f" ({self._date_label(year, month, day)})"
        self.header.setText(title)
        self.close_button.setToolTip(trans("action.close"))

    def set_date(self, year: int, month: int, day: int):
        """Set the date currently edited by the popup."""
        self.current_date = (int(year), int(month), int(day))
        self.refresh_translation()

    def is_date(self, year: int, month: int, day: int) -> bool:
        """Return True when the popup currently belongs to the given date."""
        return self.current_date == (int(year), int(month), int(day))

    def show_for(self, anchor_rect: QRect = None):
        """Show the popup next to a calendar cell and keep it on-screen."""
        self.refresh_translation()

        if anchor_rect is not None and anchor_rect.isValid():
            screen = QApplication.screenAt(anchor_rect.center())
            if screen is None:
                screen = QApplication.primaryScreen()

            x = anchor_rect.right() + self.MARGIN
            y = anchor_rect.top()

            if screen is not None:
                available = screen.availableGeometry()
                if x + self.width() > available.right():
                    x = anchor_rect.left() - self.width() - self.MARGIN
                if x < available.left():
                    x = max(available.left(), min(anchor_rect.left(), available.right() - self.width()))
                if y + self.height() > available.bottom():
                    y = available.bottom() - self.height()
                y = max(available.top(), y)

            self.move(x, y)

        self.show()
        self.raise_()
        self.activateWindow()
        if self.editor is not None:
            self.editor.setFocus(Qt.OtherFocusReason)
