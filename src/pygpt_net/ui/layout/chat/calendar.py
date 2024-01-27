#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 11:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QSplitter, QSizePolicy

from pygpt_net.ui.widget.calendar.select import CalendarSelect
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.textarea.calendar_note import CalendarNote
from pygpt_net.utils import trans


class Calendar:
    def __init__(self, window=None):
        """
        Calendar UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup calendar

        :return: QWidget
        """
        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.setup_calendar())
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_calendar(self) -> QHBoxLayout:
        """
        Setup calendar

        :return: QSplitter
        """
        # calendar
        self.window.ui.calendar['select'] = CalendarSelect(self.window)
        self.window.ui.calendar['select'].setMinimumHeight(200)
        self.window.ui.calendar['select'].setMinimumWidth(200)
        self.window.ui.calendar['select'].setGridVisible(True)

        self.window.ui.calendar['note'] = CalendarNote(self.window)

        self.window.ui.nodes['tip.output.tab.calendar'] = HelpLabel(trans('tip.output.tab.calendar'), self.window)

        # note
        self.window.ui.calendar['note.label'] = QLabel(trans('calendar.note.label'))
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.calendar['note.label'])
        layout.addWidget(self.window.ui.calendar['note'])
        layout.addWidget(self.window.ui.nodes['tip.output.tab.calendar'])
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)

        # layout / splitter
        self.window.ui.splitters['calendar'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['calendar'].addWidget(self.window.ui.calendar['select'])
        self.window.ui.splitters['calendar'].addWidget(widget)
        self.window.ui.splitters['calendar'].setStretchFactor(0, 6)  # 60%
        self.window.ui.splitters['calendar'].setStretchFactor(1, 4)  # 40%

        return self.window.ui.splitters['calendar']

