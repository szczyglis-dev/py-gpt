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

from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox

from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.utils import trans


class ComputerEnv:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'computer_env'

    def setup(self) -> QWidget:
        """
        Setup indexes

        :return: QWidget
        """
        layout = self.setup_env()
        nodes = self.window.ui.nodes
        widget = QWidget()
        widget.setLayout(layout)
        nodes['env.widget'] = widget
        return widget

    def _on_env_index_changed(self, index: int) -> None:
        nodes = self.window.ui.nodes
        cbox = nodes.get(self.id)
        if cbox is None:
            return
        data = cbox.itemData(index)
        self.window.controller.ui.on_computer_env_changed(data)

    def setup_env(self) -> QHBoxLayout:
        """
        Setup list of environments

        :return: QVBoxLayout
        """

        nodes = self.window.ui.nodes
        label = TitleLabel(trans("toolbox.env.label"))
        nodes['env.label'] = label

        cbox = QComboBox()
        for text, data in (
            ("Browser", "browser"),
            ("Windows", "windows"),
            ("Linux", "linux"),
            ("Mac", "mac"),
        ):
            cbox.addItem(text, data)
        cbox.setMinimumWidth(40)

        cbox.currentIndexChanged.connect(self._on_env_index_changed)
        nodes[self.id] = cbox

        layout = QHBoxLayout()
        layout.addWidget(label, 0)
        layout.addWidget(cbox, 1)
        layout.setContentsMargins(2, 5, 5, 5)
        return layout