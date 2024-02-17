#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.17 15:00:00                  #
# ================================================== #

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QPushButton, QComboBox, QScrollArea

from pygpt_net.ui.widget.draw.painter import PainterWidget
from pygpt_net.ui.widget.element.labels import HelpLabel
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

        :return: QVBoxLayout
        """
        self.window.ui.painter = PainterWidget(self.window)

        top = QHBoxLayout()

        key = 'painter.btn.brush'
        self.window.ui.nodes[key] = QRadioButton(trans('painter.mode.paint'))
        self.window.ui.nodes[key].setChecked(True)
        self.window.ui.nodes[key].toggled.connect(self.window.controller.painter.common.set_brush_mode)
        top.addWidget(self.window.ui.nodes[key])

        key = 'painter.btn.erase'
        self.window.ui.nodes[key] = QRadioButton(trans('painter.mode.erase'))
        self.window.ui.nodes[key].toggled.connect(self.window.controller.painter.common.set_erase_mode)
        top.addWidget(self.window.ui.nodes[key])

        key = 'painter.select.brush.size'
        sizes = self.window.controller.painter.common.get_sizes()
        self.window.ui.nodes[key] = QComboBox()
        self.window.ui.nodes[key].addItems(sizes)
        self.window.ui.nodes[key].currentTextChanged.connect(
            self.window.controller.painter.common.change_brush_size)
        self.window.ui.nodes[key].setMinimumContentsLength(10)
        self.window.ui.nodes[key].setSizeAdjustPolicy(QComboBox.AdjustToContents)
        top.addWidget(self.window.ui.nodes[key])

        key = 'painter.select.brush.color'
        self.window.ui.nodes[key] = QComboBox()
        colors = self.window.controller.painter.common.get_colors()
        for color_name, color_value in colors.items():
            pixmap = QPixmap(100, 100)
            pixmap.fill(color_value)
            icon = QIcon(pixmap)
            self.window.ui.nodes[key].addItem(icon, color_name, color_value)
        self.window.ui.nodes[key].currentTextChanged.connect(
            self.window.controller.painter.common.change_brush_color)
        self.window.ui.nodes[key].setMinimumContentsLength(10)
        self.window.ui.nodes[key].setSizeAdjustPolicy(QComboBox.AdjustToContents)
        top.addWidget(self.window.ui.nodes[key])

        key = 'painter.select.canvas.size'
        canvas_sizes = self.window.controller.painter.common.get_canvas_sizes()
        self.window.ui.nodes[key] = QComboBox()
        self.window.ui.nodes[key].addItems(canvas_sizes)
        self.window.ui.nodes[key].setMinimumContentsLength(20)
        self.window.ui.nodes[key].setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.window.ui.nodes[key].currentTextChanged.connect(
            self.window.controller.painter.common.change_canvas_size)
        top.addWidget(self.window.ui.nodes[key])

        top.addStretch(1)
        self.window.ui.nodes['painter.btn.capture'] = QPushButton(trans('painter.btn.capture'))
        self.window.ui.nodes['painter.btn.capture'].clicked.connect(self.window.controller.painter.capture.use)
        top.addWidget(self.window.ui.nodes['painter.btn.capture'])

        self.window.ui.nodes['painter.btn.camera.capture'] = QPushButton(trans('painter.btn.camera.capture'))
        self.window.ui.nodes['painter.btn.camera.capture'].clicked.connect(self.window.controller.painter.capture.camera)
        top.addWidget(self.window.ui.nodes['painter.btn.camera.capture'])

        self.window.ui.nodes['painter.btn.clear'] = QPushButton(trans('painter.btn.clear'))
        self.window.ui.nodes['painter.btn.clear'].clicked.connect(self.window.ui.painter.clear_image)
        top.addWidget(self.window.ui.nodes['painter.btn.clear'])

        self.window.ui.painter_scroll = QScrollArea()
        self.window.ui.painter_scroll.setWidget(self.window.ui.painter)
        self.window.ui.painter_scroll.setWidgetResizable(True)

        self.window.ui.nodes['tip.output.tab.draw'] = HelpLabel(trans('tip.output.tab.draw'), self.window)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget( self.window.ui.painter_scroll)
        layout.addWidget(self.window.ui.nodes['tip.output.tab.draw'])
        layout.setContentsMargins(0, 0, 0, 0)

        return layout



