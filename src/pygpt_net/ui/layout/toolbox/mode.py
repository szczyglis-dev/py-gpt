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

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.lists.mode_combo import ModeCombo
from pygpt_net.utils import trans


class Mode:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'prompt.mode'
        self._label_key = f'{self.id}.label'
        self._label_trans_key = 'toolbox.mode.label'

    def setup(self) -> QWidget:
        """
        Setup mode

        :return: QWidget
        """
        widget = QWidget()
        widget.setLayout(self.setup_list())
        return widget

    def setup_list(self) -> QVBoxLayout:
        """
        Setup list

        :return: QVBoxLayout
        """
        ui_nodes = self.window.ui.nodes

        label = ui_nodes.get(self._label_key)
        label_text = trans(self._label_trans_key)
        if label is None:
            label = TitleLabel(label_text)
            ui_nodes[self._label_key] = label
        else:
            label.setText(label_text)

        combo = ui_nodes.get(self.id)
        if combo is None:
            combo = ModeCombo(self.window, self.id)
            ui_nodes[self.id] = combo

        header_layout = QVBoxLayout()
        header_layout.addWidget(label)
        header_layout.setContentsMargins(5, 5, 0, 0)

        layout = QVBoxLayout()
        layout.addLayout(header_layout)
        layout.addWidget(combo)
        layout.addStretch()
        layout.setContentsMargins(2, 5, 5, 5)

        return layout