#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 15:00:00                  #
# ================================================== #

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QPushButton, QComboBox, QScrollArea
from PySide6.QtCore import QSize

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

            # Zoom combo (view-only scale) placed to the right of canvas size
            key = 'painter.select.zoom'
            if nodes.get(key) is None:
                cb = QComboBox()
                cb.setMinimumContentsLength(8)
                cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)

                # Preferred preset steps from widget; fallback to defaults
                steps = []
                if hasattr(ui.painter, 'get_zoom_steps_percent'):
                    try:
                        steps = ui.painter.get_zoom_steps_percent()
                    except Exception:
                        steps = []
                if not steps:
                    steps = [10, 25, 50, 75, 100, 150, 200, 500, 1000]

                cb.addItems([f"{p}%" for p in steps])

                # User -> widget
                cb.currentTextChanged.connect(ui.painter.on_zoom_combo_changed)

                # Widget -> combo (also covers CTRL+wheel and programmatic changes)
                def _sync_zoom_combo_from_widget(z):
                    """Keep zoom combobox in sync with the widget's zoom."""
                    percent = int(round(float(z) * 100))
                    label = f"{percent}%"
                    cb.blockSignals(True)
                    idx = cb.findText(label)
                    if idx >= 0:
                        cb.setCurrentIndex(idx)
                    else:
                        # Insert missing value keeping ascending order
                        items = [cb.itemText(i) for i in range(cb.count())]
                        if label not in items:
                            items.append(label)
                            try:
                                items_sorted = sorted(
                                    set(items),
                                    key=lambda s: float(s.replace('%', '').strip())
                                )
                            except Exception:
                                items_sorted = items
                            cb.clear()
                            cb.addItems(items_sorted)
                        cb.setCurrentText(label)
                    cb.blockSignals(False)

                # Keep reference to prevent GC of the inner function
                cb._sync_zoom_combo_from_widget = _sync_zoom_combo_from_widget
                if hasattr(ui.painter, 'zoomChanged'):
                    ui.painter.zoomChanged.connect(cb._sync_zoom_combo_from_widget)

                # Initial label; actual value will be set by load_zoom below
                cb.setCurrentText("100%")
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
        # Zoom combo placed right after canvas size
        top.addWidget(nodes['painter.select.zoom'])
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
            # Must be False to allow content widget to grow/shrink with zoom and show scrollbars
            ui.painter_scroll.setWidgetResizable(False)
        else:
            if ui.painter_scroll.widget() is not ui.painter:
                ui.painter_scroll.setWidget(ui.painter)
            ui.painter_scroll.setWidgetResizable(False)

        if nodes.get('tip.output.tab.draw') is None:
            nodes['tip.output.tab.draw'] = HelpLabel(trans('tip.output.tab.draw'), self.window)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(ui.painter_scroll)
        layout.addWidget(nodes['tip.output.tab.draw'])
        layout.setContentsMargins(0, 0, 0, 0)

        return layout