#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 06:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPainter, QPen
from PySide6.QtWidgets import QTextEdit, QApplication, QMenu, QWidget

from pygpt_net.utils import trans


class PainterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.drawing = False
        self.brushSize = 3
        self.brushColor = Qt.black
        self.lastPoint = QPoint()

    def mousePressEvent(self, event):
        self.drawing = True
        self.lastPoint = event.pos()

    def setBrushColor(self, color):
        self.brushColor = color

    def clearImage(self):
        self.image.fill(Qt.white)
        self.update()

    def setBrushSize(self, size):
        self.brushSize = size

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            painter = QPainter(self.image)
            painter.setPen(QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(self.lastPoint, event.pos())
            self.lastPoint = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            self.drawing = False

    def paintEvent(self, event):
        canvasPainter = QPainter(self)
        canvasPainter.drawImage(self.rect(), self.image, self.image.rect())

    def resizeEvent(self, event):
        if self.image.size() != self.size():
            newImage = QImage(self.size(), QImage.Format_RGB32)
            newImage.fill(Qt.white)
            painter = QPainter(newImage)
            painter.drawImage(QPoint(0, 0), self.image)
            self.image = newImage
