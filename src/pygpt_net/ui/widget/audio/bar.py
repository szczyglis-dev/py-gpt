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
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QWidget

import pygpt_net.icons_rc

class InputBar(QWidget):
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
        palette = self.palette()
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        level_width = (self._level / 100.0) * self.width()
        painter.setBrush(palette.color(QPalette.ButtonText))
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


class OutputBar(QWidget):
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
        palette = self.palette()
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        level_width = (self._level / 100.0) * self.width()
        painter.setBrush(palette.color(QPalette.ButtonText))
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