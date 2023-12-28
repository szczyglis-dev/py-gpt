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
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget


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
