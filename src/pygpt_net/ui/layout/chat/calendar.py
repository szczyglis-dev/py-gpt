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

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QRadioButton, QCheckBox, \
    QTabWidget, QWidget

from pygpt_net.ui.layout.chat.attachments import Attachments
from pygpt_net.ui.layout.chat.attachments_uploaded import AttachmentsUploaded
from pygpt_net.ui.layout.status import Status
from pygpt_net.ui.widget.audio.input import AudioInput
from pygpt_net.ui.widget.calendar.select import CalendarSelect
from pygpt_net.ui.widget.textarea.input import ChatInput
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
        layout.addLayout(self.setup_calendar())

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_calendar(self) -> QHBoxLayout:
        """
        Setup calendar

        :return: QHBoxLayout
        """
        # calendar
        self.window.ui.calendar['select'] = CalendarSelect(self.window)
        self.window.ui.calendar['select'].setMinimumHeight(200)
        self.window.ui.calendar['select'].setMinimumWidth(200)
        self.window.ui.calendar['select'].setGridVisible(True)

        # layout
        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.calendar['select'])

        return layout

