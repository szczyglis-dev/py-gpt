#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 22:05:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QDate, QLocale, QTime, QTimer
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QSizePolicy, QRadioButton, QCheckBox, QButtonGroup

from pygpt_net.ui.widget.calendar.note import CalendarNotePopup
from pygpt_net.ui.widget.calendar.select import CalendarSelect
from pygpt_net.ui.widget.element.checkbox import ColorCheckbox
from pygpt_net.ui.widget.element.labels import HelpLabel, IconLabel
from pygpt_net.ui.widget.textarea.calendar_note import CalendarNote
from pygpt_net.utils import trans


# Toggle horizontal centering of the responsive month grid.
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


class Calendar:
    __slots__ = ('window',)

    def __init__(self, window=None):
        """
        Calendar UI

        :param window: Window instance
        """
        self.window = window

    def init(self):
        """
        Initialize painter

        :return: QWidget
        """
        ui = self.window.ui
        ui.calendar['select'] = CalendarSelect(self.window)
        ui.calendar['select'].setMinimumSize(200, 200)
        ui.calendar['select'].setGridVisible(True)
        ui.calendar['note'] = CalendarNote(self.window)
        ui.calendar['note.popup'] = CalendarNotePopup(self.window, ui.calendar['note'])

    def setup(self) -> QWidget:
        """
        Setup calendar

        :return: QWidget
        """
        self.init()
        body = self.window.core.tabs.from_widget(self.setup_calendar())
        body.append(self.window.ui.calendar['note'])
        body.append(self.window.ui.calendar['select'])
        body.add_ref(self.window.ui.calendar['note.popup'])
        return body

    def _on_filter_id_clicked(self, id_: int) -> None:
        key = "all" if id_ == 0 else ("pinned" if id_ == 1 else "indexed")
        self.window.controller.ctx.common.toggle_display_filter(key)

    def _on_counters_all_toggled(self, checked: bool) -> None:
        self.window.controller.calendar.note.toggle_counters_all(checked)

    def _current_weekday_text(self) -> str:
        """Return today's full weekday name in the active application language."""
        today = QDate.currentDate()
        try:
            lang = self.window.core.config.get_lang() or "en"
            weekday = QLocale(lang).dayName(
                today.dayOfWeek(),
                QLocale.FormatType.LongFormat,
            ).strip().rstrip(".")
            if weekday:
                return weekday
        except Exception:
            pass
        return today.toString("dddd")

    def _update_clock(self) -> None:
        """Refresh the weekday and clock labels from the same timer."""
        nodes = self.window.ui.nodes
        weekday = nodes.get('calendar.clock.weekday')
        clock = nodes.get('calendar.clock')
        if weekday is not None:
            weekday.setText(self._current_weekday_text())
        if clock is not None:
            clock.setText(QTime.currentTime().toString("HH:mm"))

    def setup_filters(self) -> QWidget:
        """
        Setup calendar filters

        :return: QWidget
        """
        ui = self.window.ui
        nodes = ui.nodes

        label_existing = nodes.get('filter.ctx.label')
        if label_existing is None:
            layout = QHBoxLayout()
            widget = QWidget()
            rows = QVBoxLayout()
            widget.setLayout(rows)

            label = QLabel(trans("filter.ctx.label"), widget)

            radio_all = QRadioButton(trans("filter.ctx.radio.all"), widget)
            radio_pinned = QRadioButton(trans("filter.ctx.radio.pinned"), widget)
            radio_indexed = QRadioButton(trans("filter.ctx.radio.indexed"), widget)

            counters_all = QCheckBox(trans("filter.ctx.counters.all"), widget)

            layout.addWidget(label)
            layout.addWidget(radio_all)
            layout.addWidget(radio_pinned)
            layout.addWidget(radio_indexed)
            layout.addWidget(counters_all)
            layout.addStretch()

            nodes['filter.ctx.labels'] = ColorCheckbox(self.window)
            nodes['calendar.clock.weekday'] = QLabel(self._current_weekday_text(), widget)
            nodes['calendar.clock.weekday'].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            nodes['calendar.clock.icon'] = IconLabel(":/icons/clock.svg", widget, hover=False)
            nodes['calendar.clock'] = QLabel(QTime.currentTime().toString("HH:mm"), widget)
            nodes['calendar.clock'].setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            labels_layout = QHBoxLayout()
            labels_layout.setContentsMargins(0, 0, 0, 0)
            labels_layout.addWidget(nodes['filter.ctx.labels'], 1)
            labels_layout.addWidget(nodes['calendar.clock.weekday'], 0, Qt.AlignRight | Qt.AlignVCenter)
            labels_layout.addWidget(nodes['calendar.clock.icon'], 0, Qt.AlignRight | Qt.AlignVCenter)
            labels_layout.addWidget(nodes['calendar.clock'], 0, Qt.AlignRight | Qt.AlignVCenter)

            clock_timer = QTimer(widget)
            clock_timer.setInterval(1000)
            clock_timer.timeout.connect(self._update_clock)
            clock_timer.start()
            nodes['calendar.clock.timer'] = clock_timer

            rows.addLayout(layout)
            rows.addLayout(labels_layout)

            group = QButtonGroup(widget)
            group.setExclusive(True)
            group.addButton(radio_all, 0)
            group.addButton(radio_pinned, 1)
            group.addButton(radio_indexed, 2)
            group.idClicked.connect(self._on_filter_id_clicked)

            counters_all.toggled.connect(self._on_counters_all_toggled)

            nodes['filter.ctx.label'] = label
            nodes['filter.ctx.radio.all'] = radio_all
            nodes['filter.ctx.radio.pinned'] = radio_pinned
            nodes['filter.ctx.radio.indexed'] = radio_indexed
            nodes['filter.ctx.counters.all'] = counters_all
        else:
            widget = nodes['filter.ctx.label'].parentWidget()
            nodes['filter.ctx.label'].setText(trans("filter.ctx.label"))
            nodes['filter.ctx.radio.all'].setText(trans("filter.ctx.radio.all"))
            nodes['filter.ctx.radio.pinned'].setText(trans("filter.ctx.radio.pinned"))
            nodes['filter.ctx.radio.indexed'].setText(trans("filter.ctx.radio.indexed"))
            nodes['filter.ctx.counters.all'].setText(trans("filter.ctx.counters.all"))

        self._update_clock()

        desired = bool(self.window.core.config.get("ctx.counters.all"))
        if nodes['filter.ctx.counters.all'].isChecked() != desired:
            nodes['filter.ctx.counters.all'].setChecked(desired)

        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return widget

    def setup_calendar(self) -> QWidget:
        """
        Setup calendar

        :return: QWidget
        """
        ui = self.window.ui
        calendar = ui.calendar

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(6)

        # Keep the month view inside the existing Calendar tab hierarchy.
        # The host is managed by Qt's normal layout, while the calendar itself
        # is resized to the largest square that fits. Horizontal centering can
        # be toggled with CENTER_CALENDAR at the top of this module.
        calendar_host = CalendarSquareHost(calendar['select'])
        layout.addWidget(calendar_host, 1)

        filters = self.setup_filters()
        filters.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(filters, 0)

        if ui.nodes.get('tip.output.tab.calendar') is None:
            ui.nodes['tip.output.tab.calendar'] = HelpLabel(
                trans('tip.output.tab.calendar'),
                self.window,
            )
        layout.addWidget(ui.nodes['tip.output.tab.calendar'], 0)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Day notes are edited in a floating, resizable popup.  The calendar
        # no longer needs a horizontal splitter or a permanently visible note
        # textarea on the right.
        ui.splitters.pop('calendar', None)

        return self.window.core.tabs.from_widget(widget)
