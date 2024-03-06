#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 02:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QWidget, QCheckBox, QHBoxLayout, QLabel
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt

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

        for id, status in labels.items():
            self.boxes[id] = QCheckBox()
            self.boxes[id].stateChanged.connect(
                lambda state, idx=id: self.update_colors(state, idx)
            )
            pixmap = QPixmap(20, 20)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(status['color'])
            painter.drawRect(0, 0, 20, 20)
            painter.end()

            self.boxes[id].setIcon(pixmap)
            layout.addWidget(self.boxes[id])

        layout.addStretch()
        self.setLayout(layout)

    def update_colors(self, state: int, idx: int):
        """
        Update selected colors list

        :param state: checkbox state
        :param idx: color index
        """
        if state == 2:
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
            self.boxes[idx].setChecked(True)
