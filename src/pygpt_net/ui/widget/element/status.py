#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.28 00:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from datetime import datetime
from pygpt_net.utils import trans


class BottomStatus:
    def __init__(self, window=None):
        self.window = window
        self.timer = QLabel(parent=self.window)
        self.timer.setObjectName("StatusBarTimer")
        self.msg = QLabel(parent=self.window)
        self.msg.setObjectName("StatusBarMessage")
        self.set_text(trans('status.started'))

    def set_text(self, text):
        """Set status text"""
        self.msg.setText(text)
        if text:
            now = datetime.now()
            self.timer.setText(now.strftime("%H:%M"))
        else:
            self.timer.setText("")

    def setText(self, text):
        """Fallback for set_text method"""
        self.set_text(text)

    def text(self) -> str:
        """Get status text"""
        return self.msg.text()

    def setup(self):
        """Setup status bar widget"""
        self.timer.setText("00:00")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self.timer)
        layout.addWidget(self.msg)
        layout.addStretch()
        widget = QWidget(self.window)
        widget.setLayout(layout)
        return widget