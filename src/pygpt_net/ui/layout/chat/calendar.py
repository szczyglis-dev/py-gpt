#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.28 13:31:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QDateTime, QLocale, QTimer
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QSizePolicy, QRadioButton, QCheckBox, QButtonGroup

from pygpt_net.ui.widget.calendar.note import CalendarNotePopup
from pygpt_net.ui.widget.calendar.select import CalendarSelect
from pygpt_net.ui.widget.element.checkbox import ColorCheckbox
from pygpt_net.ui.widget.element.labels import HelpLabel
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

    @staticmethod
    def _date_fields(format_str: str) -> list[tuple[str, int, int]]:
        """Return Qt date-format fields outside quoted literals."""
        fields = []
        i = 0
        quoted = False
        length = len(format_str)

        while i < length:
            char = format_str[i]
            if char == "'":
                # Two consecutive apostrophes are an escaped literal apostrophe.
                if i + 1 < length and format_str[i + 1] == "'":
                    i += 2
                    continue
                quoted = not quoted
                i += 1
                continue

            if not quoted and char in "yMd":
                end = i + 1
                while end < length and format_str[end] == char:
                    end += 1
                fields.append((char, i, end))
                i = end
                continue
            i += 1

        return fields

    @classmethod
    def _date_format_without_year(cls, format_str: str) -> str:
        """Remove the year and its adjacent separator/literal from a Qt date format."""
        fields = cls._date_fields(format_str)
        year = next((field for field in fields if field[0] == "y"), None)
        if year is None:
            return format_str.strip()

        _, year_start, year_end = year
        previous = next((field for field in reversed(fields) if field[2] <= year_start), None)
        following = next((field for field in fields if field[1] >= year_end), None)

        if previous is None and following is not None:
            # E.g. Japanese/Chinese: yyyy年M月d日 -> M月d日
            result = format_str[following[1]:]
        elif following is None and previous is not None:
            # E.g. Polish/Spanish/English: remove the separator or literal that
            # belongs to the trailing year as well (", yyyy", " de yyyy", etc.).
            result = format_str[:previous[2]]
        else:
            result = format_str[:year_start] + format_str[year_end:]

        return " ".join(result.strip(" ,;/").split())

    @staticmethod
    def _format_fields(format_str: str, chars: str) -> list[tuple[str, int, int]]:
        """Return selected Qt date/time-format fields outside quoted literals."""
        fields = []
        i = 0
        quoted = False
        length = len(format_str)

        while i < length:
            char = format_str[i]
            if char == "'":
                if i + 1 < length and format_str[i + 1] == "'":
                    i += 2
                    continue
                quoted = not quoted
                i += 1
                continue

            if not quoted and char in chars:
                end = i + 1
                while end < length and format_str[end] == char:
                    end += 1
                fields.append((char, i, end))
                i = end
                continue
            i += 1

        return fields

    @staticmethod
    def _format_literal(text: str) -> str:
        """Decode quoted literals from a Qt date/time format fragment."""
        result = []
        i = 0
        quoted = False
        while i < len(text):
            if text[i] == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    result.append("'")
                    i += 2
                    continue
                quoted = not quoted
                i += 1
                continue
            result.append(text[i])
            i += 1
        return "".join(result)

    @classmethod
    def _date_time_layout(cls, locale: QLocale) -> tuple[bool, str]:
        """Return native date/time order and separator for the locale."""
        format_str = locale.dateTimeFormat(QLocale.FormatType.ShortFormat)
        date_fields = cls._format_fields(format_str, "yMd")
        time_fields = cls._format_fields(format_str, "hHmszAtap")
        if not date_fields or not time_fields:
            return True, ", "

        date_start = min(field[1] for field in date_fields)
        date_end = max(field[2] for field in date_fields)
        time_start = min(field[1] for field in time_fields)
        time_end = max(field[2] for field in time_fields)

        if date_end <= time_start:
            separator = cls._format_literal(format_str[date_end:time_start])
            return True, separator or " "
        if time_end <= date_start:
            separator = cls._format_literal(format_str[time_end:date_start])
            return False, separator or " "
        return True, ", "

    def _active_locale(self) -> QLocale:
        """Return the Qt locale matching the language selected in PyGPT."""
        try:
            lang = self.window.core.config.get_lang() or ""
            if lang:
                locale = QLocale(lang)
                if locale.language() != QLocale.Language.C:
                    return locale
        except Exception:
            pass
        return QLocale.system()

    def _current_date_time_text(self) -> str:
        """Return a localized weekday/date/time string without the year."""
        now = QDateTime.currentDateTime()
        locale = self._active_locale()

        date_format = locale.dateFormat(QLocale.FormatType.LongFormat)
        date_format = self._date_format_without_year(date_format)
        date_text = locale.toString(now.date(), date_format).strip()

        # Most Qt long-date formats already contain the weekday. Add it only
        # when the locale's native format omits it.
        has_weekday = any(
            field == "d" and end - start >= 3
            for field, start, end in self._date_fields(date_format)
        )
        if not has_weekday:
            weekday = locale.dayName(
                now.date().dayOfWeek(),
                QLocale.FormatType.LongFormat,
            ).strip()
            if weekday:
                date_text = f"{weekday}, {date_text}"

        time_text = locale.toString(
            now.time(),
            QLocale.FormatType.ShortFormat,
        ).strip()
        date_first, separator = self._date_time_layout(locale)
        if date_first:
            return f"{date_text}{separator}{time_text}"
        return f"{time_text}{separator}{date_text}"

    def _update_clock(self) -> None:
        """Refresh the localized date/time label."""
        clock = self.window.ui.nodes.get('calendar.clock')
        if clock is not None:
            clock.setText(self._current_date_time_text())

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
            nodes['calendar.clock'] = QLabel(self._current_date_time_text(), widget)
            nodes['calendar.clock'].setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            labels_layout = QHBoxLayout()
            labels_layout.setContentsMargins(0, 0, 0, 0)
            labels_layout.addWidget(nodes['filter.ctx.labels'], 1)
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
