#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.24 22:00:00                  #
# ================================================== #

from PySide6.QtCore import (
    Qt, QSize, QPoint, QPointF, QRectF,
    QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup,
    Slot, Property, QEvent)

from PySide6.QtWidgets import QCheckBox
from PySide6.QtGui import QColor, QBrush, QPaintEvent, QPen, QPainter, QPalette


class AnimToggle(QCheckBox):

    # Based on widget from: https://www.pythonguis.com/tutorials/pyside6-animated-widgets/

    _transparent_pen = QPen(Qt.transparent)
    _light_grey_pen = QPen(Qt.lightGray)

    def __init__(self, title="", parent=None):
        super().__init__()
        self.setText(title)
        self.option = None

        # Initialize the colors based on the current palette
        self.updateColors()

        # Setup the rest of the widget.
        self.setContentsMargins(8, 0, 8, 0)
        self.setMaximumWidth(58)
        self._handle_position = 0
        self._pulse_radius = 0

        # Setup animations
        self.animation = QPropertyAnimation(self, b"handle_position", self)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.setDuration(200)  # time in ms

        self.pulse_anim = QPropertyAnimation(self, b"pulse_radius", self)
        self.pulse_anim.setDuration(350)  # time in ms
        self.pulse_anim.setStartValue(10)
        self.pulse_anim.setEndValue(20)

        self.animations_group = QSequentialAnimationGroup()
        self.animations_group.addAnimation(self.animation)
        self.animations_group.addAnimation(self.pulse_anim)

        self.stateChanged.connect(self.setup_animation)

    def updateColors(self):
        # Get colors from the palette.
        palette = self.palette()
        #bar_color = QPen(Qt.lightGray).color()
        bar_color = QColor("#969696")
        #bar_checked_color = palette.color(QPalette.Dark)
        bar_checked_color = QColor("#969696")
        bar_color.setAlpha(0x80)
        handle_color = palette.color(QPalette.Dark)
        handle_checked_color = palette.color(QPalette.ButtonText)

        # Create semi-transparent colors for the pulse effect
        pulse_unchecked_color = bar_color.darker(110)
        pulse_checked_color = bar_checked_color.lighter(130)
        pulse_unchecked_color.setAlpha(0x44)
        pulse_checked_color.setAlpha(0x44)

        # Now set the brushes
        self._bar_brush = QBrush(bar_color)
        self._bar_checked_brush = QBrush(bar_checked_color)
        self._handle_brush = QBrush(handle_color)
        self._handle_checked_brush = QBrush(handle_checked_color)
        self._pulse_unchecked_animation = QBrush(pulse_unchecked_color)
        self._pulse_checked_animation = QBrush(pulse_checked_color)

        # Update the widget to redraw with new colors
        self.update()

    def event(self, e):
        if e.type() == QEvent.PaletteChange:
            self.updateColors()
        return super().event(e)

    def sizeHint(self):
        return QSize(58, 45)

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    @Slot(int)
    def setup_animation(self, value):
        self.animations_group.stop()
        if value:
            self.animation.setEndValue(1)
        else:
            self.animation.setEndValue(0)
        self.animations_group.start()

    def paintEvent(self, e: QPaintEvent):
        contRect = self.contentsRect()
        handleRadius = round(0.24 * contRect.height())

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(self._transparent_pen)

        barRect = QRectF(
            0, 0,
            contRect.width() - handleRadius, 0.40 * contRect.height()
        )
        barRect.moveCenter(contRect.center())
        rounding = barRect.height() / 2

        # The handle will move along this line
        trailLength = contRect.width() - 2 * handleRadius

        xPos = contRect.x() + handleRadius + trailLength * self._handle_position

        if self.pulse_anim.state() == QPropertyAnimation.Running:
            p.setBrush(
                self._pulse_checked_animation if
                self.isChecked() else self._pulse_unchecked_animation)
            p.drawEllipse(QPointF(xPos, barRect.center().y()),
                          self._pulse_radius, self._pulse_radius)

        if self.isChecked():
            p.setBrush(self._bar_checked_brush)
            p.drawRoundedRect(barRect, rounding, rounding)
            p.setBrush(self._handle_checked_brush)
        else:
            p.setBrush(self._bar_brush)
            p.drawRoundedRect(barRect, rounding, rounding)
            p.setPen(self._light_grey_pen)
            p.setBrush(self._handle_brush)

        p.drawEllipse(
            QPointF(xPos, barRect.center().y()),
            handleRadius, handleRadius)

        p.end()

    @Property(float)
    def handle_position(self):
        return self._handle_position

    @handle_position.setter
    def handle_position(self, pos):
        # Update the position and redraw
        self._handle_position = pos
        self.update()

    @Property(float)
    def pulse_radius(self):
        return self._pulse_radius

    @pulse_radius.setter
    def pulse_radius(self, pos):
        # Update the pulse radius and redraw
        self._pulse_radius = pos
        self.update()