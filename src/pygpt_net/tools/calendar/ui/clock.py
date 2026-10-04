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
"""Locale-aware date/time label with an owned timer."""
from PySide6.QtCore import QDateTime, QLocale, QTimer

class Clock:
    def __init__(self, window, label):
        self.window = window
        self.label = label
        self.timer = QTimer(label)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start()
        self._update_clock()

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
        clock = self.label
        if clock is not None:
            clock.setText(self._current_date_time_text())


