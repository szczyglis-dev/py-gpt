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

from PySide6.QtWidgets import QWidget, QCheckBox, QHBoxLayout, QLabel
from PySide6.QtGui import QPainter, QPixmap, QIcon
from PySide6.QtCore import Qt, QSize

from pygpt_net.utils import trans


class ColorCheckbox(QWidget):
    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.selected = []
        self.boxes = {}
        self.build()

    def build(self):
        """Build color labels checkboxes"""
        self.window.ui.nodes['filter.ctx.label.colors'] = QLabel(trans("filter.ctx.label.colors"))
        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes['filter.ctx.label.colors'])
        layout.setContentsMargins(0, 0, 0, 0)
        labels = self.window.controller.ui.get_colors()
        icon_size = 20
        icon_qsize = QSize(icon_size, icon_size)

        for color_id, status in labels.items():
            cb = QCheckBox(self)
            pixmap = QPixmap(icon_size, icon_size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(status['color'])
            painter.drawRect(0, 0, icon_size, icon_size)
            painter.end()

            cb.setIcon(QIcon(pixmap))
            cb.setIconSize(icon_qsize)
            cb.toggled.connect(lambda checked, idx=color_id: self.update_colors(checked, idx))
            self.boxes[color_id] = cb
            layout.addWidget(cb)

        layout.addStretch()
        self.setLayout(layout)

    def update_colors(self, state, idx: int):
        """
        Update selected colors list

        :param state: checkbox state
        :param idx: color index
        """
        checked = state if isinstance(state, bool) else state == Qt.Checked
        if checked:
            if idx not in self.selected:
                self.selected.append(idx)
        else:
            if idx in self.selected:
                self.selected.remove(idx)

        self.window.controller.ctx.label_filters_changed(self.selected)

    def restore(self, selected: dict):
        """
        Restore selected colors

        :param selected: selected colors
        """
        self.selected = selected
        for idx in selected:
            cb = self.boxes.get(idx)
            if cb is not None:
                prev = cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(prev)
        self.window.controller.ctx.label_filters_changed(self.selected)