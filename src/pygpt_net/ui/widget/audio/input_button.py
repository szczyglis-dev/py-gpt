#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.16 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget, QPushButton, QVBoxLayout

from pygpt_net.core.events import Event, AppEvent
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

        self.bar = LevelBar(self)
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

        self.btn_toggle = QPushButton(trans('audio.speak.btn'))
        self.btn_toggle.clicked.connect(self.toggle_recording)
        self.btn_toggle.setToolTip(trans('audio.speak.btn.tooltip'))
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setMinimumWidth(200)

        self.bar = LevelBar(self)
        self.bar.setLevel(0)

        # status
        #self.status = QLabel("xxx")
        #self.status.setStyleSheet("color: #999; font-size: 10px; font-weight: 400; margin: 0; padding: 0; border: 0;")
        #self.status.setMaximumHeight(15)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.btn_toggle)
        #self.layout.addWidget(self.status)
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
        """Toggle recording"""
        event = Event(Event.AUDIO_INPUT_RECORD_TOGGLE)
        self.window.dispatch(event)


class LevelBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0  # level from 0.0 to 100.0
        self.setFixedSize(200, 5)  # bar size

    def setLevel(self, level):
        """
        Set volume level

        :param level: level
        """
        self._level = level
        self.update()

    def paintEvent(self, event):
        """
        Paint event

        :param event: event
        """
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        level_width = (self._level / 100.0) * self.width()
        painter.setBrush(Qt.green)
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, level_width, self.height())

    """
        # --- bar from center ---
        def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        level_width = (self._level / 100.0) * self.width()
        half_level_width = level_width / 2
        center_x = self.width() / 2
        rect_x = center_x - half_level_width
        painter.setBrush(Qt.green)
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect_x, 0, level_width, self.height())
    """