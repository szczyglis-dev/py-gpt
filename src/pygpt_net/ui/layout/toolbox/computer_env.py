#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.26 18:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QComboBox

from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        self.window.ui.nodes['env.widget'] = QWidget()
        self.window.ui.nodes['env.widget'].setLayout(layout)
        return self.window.ui.nodes['env.widget']

    def setup_env(self) -> QVBoxLayout:
        """
        Setup list of environments

        :return: QVBoxLayout
        """

        # label
        self.window.ui.nodes['env.label'] = TitleLabel(trans("toolbox.env.label"))

        # list
        self.window.ui.nodes[self.id] = QComboBox()
        self.window.ui.nodes[self.id].addItem("Browser", "browser")
        self.window.ui.nodes[self.id].addItem("Windows", "windows")
        self.window.ui.nodes[self.id].addItem("Linux", "linux")
        self.window.ui.nodes[self.id].addItem("Mac", "mac")
        self.window.ui.nodes[self.id].setMinimumWidth(40)

        # on change signal
        self.window.ui.nodes[self.id].currentIndexChanged.connect(
            lambda index: self.window.controller.ui.on_computer_env_changed(
                self.window.ui.nodes[self.id].itemData(index)))

        # rows
        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes['env.label'], 0)  # label
        layout.addWidget(self.window.ui.nodes[self.id], 1)  # combobox
        layout.setContentsMargins(2, 5, 5, 5)
        return layout