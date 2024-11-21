#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 17:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QRectF, Property, QSize, QEasingCurve, QPauseAnimation, \
    QSequentialAnimationGroup
from PySide6.QtGui import QPainter, QColor, QBrush

class Loader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._size = 10
        self._scale = 1.0
        self._base_size = 30
        self._color = QColor(100, 100, 100)
        self.setFixedSize(self._base_size, self._base_size)
        self.animation = QPropertyAnimation(self, b"scale")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0.8)
        self.animation.setEndValue(1.2)
        self.animation.setLoopCount(-1)
        self.started = False
        # self.animation.start()

    def start_anim(self):
        """Start animation."""
        if self.started:
            return
        self.animation.start()
        self.started = True

    def stop_anim(self):
        """Stop animation."""
        self.started = False
        self.animation.stop()

    def paintEvent(self, event):
        """
        Paint event

        :param event: event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        brush = QBrush(self._color)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)

        scaled_size = self._size * self._scale
        x = (self.width() - scaled_size) / 2
        y = (self.height() - scaled_size) / 2

        painter.drawEllipse(QRectF(x, y, scaled_size, scaled_size))

    def sizeHint(self):
        """Size hint"""
        return QSize(self._base_size, self._base_size)

    def getScale(self):
        """
        Get scale

        :return: scale
        """
        return self._scale

    def setScale(self, scale):
        """
        Set scale

        :param scale: scale
        """
        self._scale = scale
        self.update()

    scale = Property(float, getScale, setScale)


class Loading(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.square_size = 5
        self.total_width = 100
        self.spacing = (self.total_width - 3 * self.square_size) / 2
        self._pos1 = self._pos2 = self._pos3 = 0
        self.started = False
        self.initialized = False
        # self.start_anim()

    def sizeHint(self):
        """
        Size hint

        :return: size
        """
        return QSize(self.total_width, 5)

    def start_anim(self):
        """Start animation."""
        if self.started:
            return
        self.anim1 = self.create_animation(b"pos1", 0)
        self.anim2 = self.create_animation(b"pos2", 200)
        self.anim3 = self.create_animation(b"pos3", 400)
        self.anim1.start()
        self.anim2.start()
        self.anim3.start()
        self.started = True
        self.initialized = True

    def stop_anim(self):
        """Stop animation."""
        self.started = False
        if self.initialized:
            self.anim1.stop()
            self.anim2.stop()
            self.anim3.stop()

    def create_animation(self, property_name, delay):
        """
        Create animation

        :param property_name: property name
        :param delay: delay
        """
        sequence = QSequentialAnimationGroup()
        pause = QPauseAnimation(delay)
        sequence.addAnimation(pause)
        anim = QPropertyAnimation(self, property_name)
        anim.setDuration(800)
        anim.setStartValue(0)
        anim.setKeyValueAt(0.5, self.total_width - self.square_size)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setLoopCount(-1)
        sequence.addAnimation(anim)
        sequence.setLoopCount(-1)
        return sequence

    @Property(float)
    def pos1(self):
        """
        Position 1

        :return: position
        """
        return self._pos1

    @pos1.setter
    def pos1(self, value):
        """
        Set position 1

        :param value: value
        """
        self._pos1 = value
        self.update()

    @Property(float)
    def pos2(self):
        """
        Position 2

        :return: position
        """
        return self._pos2

    @pos2.setter
    def pos2(self, value):
        """
        Set position 2

        :param value: value
        """
        self._pos2 = value
        self.update()

    @Property(float)
    def pos3(self):
        """
        Position 3

        :return: position
        """
        return self._pos3

    @pos3.setter
    def pos3(self, value):
        """
        Set position 3

        :param value: value
        """
        self._pos3 = value
        self.update()

    def paintEvent(self, event):
        """
        Paint event

        :param event: event
        """
        painter = QPainter(self)
        y = (self.height() - self.square_size) / 2

        rect1 = QRectF(self.pos1, y, self.square_size, self.square_size)
        rect2 = QRectF(self.pos2, y, self.square_size, self.square_size)
        rect3 = QRectF(self.pos3, y, self.square_size, self.square_size)

        # colors
        #painter.fillRect(rect1, QColor("#3498db"))
        #painter.fillRect(rect2, QColor("#e74c3c"))
        #painter.fillRect(rect3, QColor("#f1c40f"))

        # gray colors
        painter.fillRect(rect1, QColor("#e0e0e0"))
        painter.fillRect(rect2, QColor("#bcbcbc"))
        painter.fillRect(rect3, QColor("#959595"))

        painter.end()