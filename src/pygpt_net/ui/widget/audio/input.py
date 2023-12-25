#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QCheckBox, QHBoxLayout, QWidget

from pygpt_net.utils import trans


class AudioInput(QWidget):
    def __init__(self, window=None):
        """
        Settings audio input options

        :param window: Window instance
        """
        super(AudioInput, self).__init__(window)
        self.window = window

        self.btn_toggle = QCheckBox(trans('audio.speak.btn'))
        self.btn_toggle.stateChanged.connect(
            lambda: self.window.controller.audio.toggle_input(self.btn_toggle.isChecked(), True))

        # status
        self.status = QLabel("")
        self.status.setStyleSheet("color: #999; font-size: 10px; font-weight: 400; margin: 0; padding: 0; border: 0;")
        self.status.setMaximumHeight(15)

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.btn_toggle)
        self.layout.addWidget(self.status)

        # self.layout.addWidget(self.stop)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)
        self.setMaximumHeight(80)

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def set_status(self, text):
        self.status.setText(text)
