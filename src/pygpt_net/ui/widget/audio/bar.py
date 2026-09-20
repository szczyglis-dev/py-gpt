#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 17:40:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QWidget

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
        level = min(max(float(level), 0.0), 100.0)
        if self._level == level:
            return
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
        center_x = self.width() / 2.0
        rect_x = center_x - (level_width / 2.0)
        painter.setBrush(palette.color(QPalette.ButtonText))
        painter.setPen(Qt.NoPen)
        painter.drawRect(
            QRectF(rect_x, 0.0, level_width, float(self.height()))
        )



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
        level = min(max(float(level), 0.0), 100.0)
        if self._level == level:
            return
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
        center_x = self.width() / 2.0
        rect_x = center_x - (level_width / 2.0)
        painter.setBrush(palette.color(QPalette.ButtonText))
        painter.setPen(Qt.NoPen)
        painter.drawRect(
            QRectF(rect_x, 0.0, level_width, float(self.height()))
        )
