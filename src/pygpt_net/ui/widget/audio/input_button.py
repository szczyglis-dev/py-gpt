#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.18 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QIcon
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget, QPushButton, QVBoxLayout

from pygpt_net.core.events import Event, AppEvent
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans
from .bar import InputBar

import pygpt_net.icons_rc

class VoiceControlButton(QWidget):
    def __init__(self, window=None):
        """
        VoiceControl button

        :param window: Window instance
        """
        super(VoiceControlButton, self).__init__(window)
        self.window = window

        self.btn_toggle = QPushButton(QIcon(":/icons/mic.svg"), trans('audio.control.btn'))
        self.btn_toggle.clicked.connect(self.toggle_recording)
        self.btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setMinimumWidth(200)

        self.bar = InputBar(self)
        self.bar.setLevel(0)

        # status
        self.status = QLabel("")
        self.status.setStyleSheet("color: #999; font-size: 10px; font-weight: 400; margin: 0; padding: 0; border: 0;")
        self.status.setMaximumHeight(15)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.btn_toggle)
        # self.layout.addWidget(self.status)
        self.layout.addWidget(self.bar)

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
        self.window.dispatch(AppEvent(AppEvent.VOICE_CONTROL_TOGGLE))  # app event


class AudioInputButton(QWidget):
    def __init__(self, window=None):
        """
        Audio input record button

        :param window: Window instance
        """
        super(AudioInputButton, self).__init__(window)
        self.window = window

        self.btn_toggle = QPushButton(QIcon(":/icons/mic.svg"), trans('audio.speak.btn'))
        self.btn_toggle.clicked.connect(self.toggle_recording)
        self.btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setMinimumWidth(200)

        self.bar = InputBar(self)
        self.bar.setLevel(0)

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.btn_toggle)
        btn_layout.addWidget(self.bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)

        self.continuous = ToggleLabel(trans('audio.speak.btn.continuous'), label_position="right")
        self.continuous.box.stateChanged.connect(
            lambda: self.window.controller.audio.toggle_continuous(
                self.continuous.box.isChecked())
        )

        self.notepad_layout = QHBoxLayout()
        self.notepad_layout.addWidget(self.continuous)
        self.notepad_layout.setContentsMargins(0, 0, 0, 0)

        self.notepad_footer = QWidget()
        self.notepad_footer.setLayout(self.notepad_layout)

        self.layout = QHBoxLayout()
        self.layout.addWidget(btn_widget)
        self.layout.addWidget(self.notepad_footer)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)
        btn_widget.setMaximumHeight(80)
        self.setMaximumHeight(120)

    def add_widget(self, widget):
        """
        Add widget to layout

        :param widget: widget
        """
        self.layout.addWidget(widget)

    def toggle_recording(self):
        """Toggle recording"""
        event = Event(Event.AUDIO_INPUT_RECORD_TOGGLE)
        self.window.dispatch(event)
