#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 04:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QPushButton, QComboBox

from pygpt_net.ui.widget.draw.painter import PainterWidget
from pygpt_net.utils import trans


class Painter:
    def __init__(self, window=None):
        """
        Painter UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup painter

        :return: QWidget
        """
        widget = QWidget()
        widget.setLayout(self.setup_painter())

        return widget

    def setup_painter(self) -> QVBoxLayout:
        """
        Setup painter

        :return: QSplitter
        """
        self.window.ui.painter = PainterWidget()

        topLayout = QHBoxLayout()

        self.window.ui.nodes['painter.btn.brush'] = QRadioButton(trans('painter.mode.paint'))
        self.window.ui.nodes['painter.btn.brush'].setChecked(True)
        self.window.ui.nodes['painter.btn.brush'].toggled.connect(self.setPaintMode)
        topLayout.addWidget(self.window.ui.nodes['painter.btn.brush'])

        self.window.ui.nodes['painter.btn.erase'] = QRadioButton(trans('painter.mode.erase'))
        self.window.ui.nodes['painter.btn.erase'].toggled.connect(self.setEraseMode)
        topLayout.addWidget(self.window.ui.nodes['painter.btn.erase'])

        self.window.ui.nodes['painter.select.brush.size'] = QComboBox()
        self.window.ui.nodes['painter.select.brush.size'].addItems(['1', '2', '3', '5', '8', '12', '15', '20', '25', '30', '50', '100', '200'])
        self.window.ui.nodes['painter.select.brush.size'].currentTextChanged.connect(self.changeBrushSize)
        self.window.ui.nodes['painter.select.brush.size'].setMinimumContentsLength(10)
        self.window.ui.nodes['painter.select.brush.size'].setSizeAdjustPolicy(QComboBox.AdjustToContents)
        topLayout.addWidget(self.window.ui.nodes['painter.select.brush.size'])

        self.window.ui.nodes['painter.select.brush.color'] = QComboBox()
        colors = {
            "Black": Qt.black,
            "Red": Qt.red,
            "Orange": QColor('orange'),
            "Yellow": Qt.yellow,
            "Green": Qt.green,
            "Blue": Qt.blue,
            "Indigo": QColor('indigo'),
            "Violet": QColor('violet')
        }
        for color_name, color_value in colors.items():
            self.window.ui.nodes['painter.select.brush.color'].addItem(color_name, color_value)
        self.window.ui.nodes['painter.select.brush.color'].currentTextChanged.connect(self.changeBrushColor)
        self.window.ui.nodes['painter.select.brush.color'].setMinimumContentsLength(10)
        self.window.ui.nodes['painter.select.brush.color'].setSizeAdjustPolicy(QComboBox.AdjustToContents)
        topLayout.addWidget(self.window.ui.nodes['painter.select.brush.color'])

        topLayout.addStretch(1)
        self.window.ui.nodes['painter.btn.capture'] = QPushButton(trans('painter.btn.capture'))
        self.window.ui.nodes['painter.btn.capture'].clicked.connect(self.captureImage)
        topLayout.addWidget(self.window.ui.nodes['painter.btn.capture'])

        self.window.ui.nodes['painter.btn.clear'] = QPushButton(trans('painter.btn.clear'))
        self.window.ui.nodes['painter.btn.clear'].clicked.connect(self.window.ui.painter.clearImage)
        topLayout.addWidget(self.window.ui.nodes['painter.btn.clear'])

        layout = QVBoxLayout()
        layout.addLayout(topLayout)
        layout.addWidget(self.window.ui.painter)
        layout.setContentsMargins(0, 0, 0, 0)

        return layout

    def setPaintMode(self, enabled):
        """
        Set the paint mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.setBrushColor(Qt.black)

    def setEraseMode(self, enabled):
        """
        Set the erase mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.setBrushColor(Qt.white)

    def changeBrushSize(self, size):
        self.window.ui.painter.setBrushSize(int(size))

    def changeBrushColor(self):
        """
        Change the brush color

        :param color_name: Color name
        """
        color = self.window.ui.nodes['painter.select.brush.color'].currentData()
        self.window.ui.painter.setBrushColor(color)

    def captureImage(self):
        """Capture current image"""
        # clear attachments before capture if needed
        if self.window.controller.attachment.is_capture_clear():
            self.window.controller.attachment.clear(True)

        try:
            # prepare filename
            now = datetime.datetime.now()
            dt = now.strftime("%Y-%m-%d_%H-%M-%S")
            name = 'cap-' + dt
            path = os.path.join(self.window.core.config.path, 'capture', name + '.png')

            # capture
            self.window.ui.painter.image.save(path)
            mode = self.window.core.config.get('mode')

            # make attachment
            dt_info = now.strftime("%Y-%m-%d %H:%M:%S")
            title = trans('painter.capture.name.prefix') + ' ' + name
            title = title.replace('cap-', '').replace('_', ' ')
            self.window.core.attachments.new(mode, title, path, False)
            self.window.core.attachments.save()
            self.window.controller.attachment.update()

            # show last capture time in status
            self.window.statusChanged.emit(trans("painter.capture.manual.captured.success") + ' ' + dt_info)
            return True

        except Exception as e:
            print("Image capture exception", e)
            self.window.core.debug.log(e)

