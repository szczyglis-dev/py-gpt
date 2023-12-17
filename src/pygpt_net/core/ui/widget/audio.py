#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.15 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QCheckBox, QHBoxLayout, QWidget, QPushButton

from ...utils import trans


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
            lambda: self.window.controller.plugins.dispatch('audio.input.toggle', self.btn_toggle.isChecked()))

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


class AudioOutput(QWidget):
    def __init__(self, window=None):
        """
        Settings audio output options

        :param window: main window
        """
        super(AudioOutput, self).__init__(window)
        self.window = window

        # stop button
        # self.stop = QPushButton("STOP")
        # self.stop.setVisible(False)
        # self.stop.setMaximumHeight(40)

        self.status = QLabel("")
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.status)
        # self.layout.addWidget(self.stop)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)

        self.setMinimumHeight(40)
        self.setMaximumHeight(40)

    def add_widget(self, widget):
        """
        Add widget to layout

        :param widget: QWidget
        """
        self.layout.addWidget(widget)

    def set_status(self, text):
        """
        Set status text
        :param text: Text to set
        """
        self.status.setText(text)
