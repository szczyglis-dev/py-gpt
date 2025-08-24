#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QPushButton, QComboBox, QScrollArea
from PySide6.QtCore import QSize

from pygpt_net.ui.widget.draw.painter import PainterWidget
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.tabs.body import TabBody
from pygpt_net.utils import trans


class Painter:
    def __init__(self, window=None):
        """
        Painter UI

        :param window: Window instance
        """
        self.window = window
        self._initialized = False

    def init(self):
        """
        Initialize painter

        :return: QWidget
        """
        ui = self.window.ui
        nodes = ui.nodes
        common = self.window.controller.painter.common

        if getattr(ui, 'painter', None) is None:
            ui.painter = PainterWidget(self.window)

        key = 'painter.btn.brush'
        if nodes.get(key) is None:
            rb = QRadioButton(trans('painter.mode.paint'))
            rb.setChecked(True)
            rb.toggled.connect(self.window.controller.painter.common.set_brush_mode)
            nodes[key] = rb

        key = 'painter.btn.erase'
        if nodes.get(key) is None:
            rb = QRadioButton(trans('painter.mode.erase'))
            rb.toggled.connect(self.window.controller.painter.common.set_erase_mode)
            nodes[key] = rb

        key = 'painter.select.brush.size'
        if nodes.get(key) is None:
            sizes = common.get_sizes()
            cb = QComboBox()
            cb.addItems(sizes)
            cb.currentTextChanged.connect(common.change_brush_size)
            cb.setMinimumContentsLength(10)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            nodes[key] = cb

        key = 'painter.select.canvas.size'
        if nodes.get(key) is None:
            canvas_sizes = common.get_canvas_sizes()
            cb = QComboBox()
            cb.addItems(canvas_sizes)
            cb.setMinimumContentsLength(20)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            cb.currentTextChanged.connect(common.change_canvas_size)
            nodes[key] = cb

        key = 'painter.select.brush.color'
        if nodes.get(key) is None:
            cb = QComboBox()
            cb.setIconSize(QSize(16, 16))
            colors = common.get_colors()
            for color_name, color_value in colors.items():
                pixmap = QPixmap(16, 16)
                pixmap.fill(color_value)
                icon = QIcon(pixmap)
                cb.addItem(icon, color_name, color_value)
            cb.currentTextChanged.connect(common.change_brush_color)
            cb.setMinimumContentsLength(10)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            nodes[key] = cb

        self._initialized = True

    def setup(self) -> QWidget:
        """
        Setup painter

        :return: QWidget
        """
        self.init()
        body = self.window.core.tabs.from_layout(self.setup_painter())
        body.append(self.window.ui.painter)
        return body

    def setup_painter(self) -> QVBoxLayout:
        """
        Setup painter

        :return: QVBoxLayout
        """
        ui = self.window.ui
        nodes = ui.nodes

        top = QHBoxLayout()
        top.addWidget(nodes['painter.btn.brush'])
        top.addWidget(nodes['painter.btn.erase'])
        top.addWidget(nodes['painter.select.brush.size'])
        top.addWidget(nodes['painter.select.brush.color'])
        top.addWidget(nodes['painter.select.canvas.size'])
        top.addStretch(1)

        if nodes.get('painter.btn.capture') is None:
            btn = QPushButton(trans('painter.btn.capture'))
            btn.clicked.connect(self.window.controller.painter.capture.use)
            nodes['painter.btn.capture'] = btn
        top.addWidget(nodes['painter.btn.capture'])

        if nodes.get('painter.btn.camera.capture') is None:
            btn = QPushButton(trans('painter.btn.camera.capture'))
            btn.clicked.connect(self.window.controller.painter.capture.camera)
            nodes['painter.btn.camera.capture'] = btn
        top.addWidget(nodes['painter.btn.camera.capture'])

        if nodes.get('painter.btn.clear') is None:
            btn = QPushButton(trans('painter.btn.clear'))
            btn.clicked.connect(ui.painter.clear_image)
            nodes['painter.btn.clear'] = btn
        top.addWidget(nodes['painter.btn.clear'])

        if getattr(ui, 'painter_scroll', None) is None:
            ui.painter_scroll = QScrollArea()
            ui.painter_scroll.setWidget(ui.painter)
            ui.painter_scroll.setWidgetResizable(True)
        else:
            if ui.painter_scroll.widget() is not ui.painter:
                ui.painter_scroll.setWidget(ui.painter)
            ui.painter_scroll.setWidgetResizable(True)

        if nodes.get('tip.output.tab.draw') is None:
            nodes['tip.output.tab.draw'] = HelpLabel(trans('tip.output.tab.draw'), self.window)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(ui.painter_scroll)
        layout.addWidget(nodes['tip.output.tab.draw'])
        layout.setContentsMargins(0, 0, 0, 0)

        return layout