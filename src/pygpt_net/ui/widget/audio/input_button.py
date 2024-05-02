#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget, QPushButton

from pygpt_net.core.access.events import AppEvent
from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans

class VoiceControlButton(QWidget):
    def __init__(self, window=None):
        """
        VoiceControl button

        :param window: Window instance
        """
        super(VoiceControlButton, self).__init__(window)
        self.window = window

        self.btn_toggle = QPushButton(trans('audio.control.btn'))
        self.btn_toggle.clicked.connect(self.toggle_recording)
        self.btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setMinimumWidth(200)

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
        """
        Add widget to layout

        :param widget: widget
        """
        self.layout.addWidget(widget)

    def set_status(self, text):
        """
        Set status text

        :param text: text
        """
        self.status.setText(text)

    def toggle_recording(self):
        """Toggle voice control"""
        self.window.core.dispatcher.dispatch(AppEvent(AppEvent.VOICE_CONTROL_TOGGLE))  # app event


class AudioInputButton(QWidget):
    def __init__(self, window=None):
        """
        Audio input record button

        :param window: Window instance
        """
        super(AudioInputButton, self).__init__(window)
        self.window = window

        self.btn_toggle = QPushButton(trans('audio.speak.btn'))
        self.btn_toggle.clicked.connect(self.toggle_recording)
        self.btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setMinimumWidth(200)

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
        """
        Add widget to layout

        :param widget: widget
        """
        self.layout.addWidget(widget)

    def set_status(self, text):
        """
        Set status text

        :param text: text
        """
        self.status.setText(text)

    def toggle_recording(self):
        """Toggle recording"""
        event = Event(Event.AUDIO_INPUT_RECORD_TOGGLE)
        self.window.core.dispatcher.dispatch(event)
