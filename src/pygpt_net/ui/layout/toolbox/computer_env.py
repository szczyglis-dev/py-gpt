#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 02:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox, QVBoxLayout

from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
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

    def on_sandbox_toggled(self, checked: bool) -> None:
        """
        Handle sandbox toggle

        :param checked: bool
        """
        self.window.controller.ui.on_computer_sandbox_toggled(checked)

    def setup_env(self) -> QVBoxLayout:
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
        nodes['computer_env'] = cbox

        # sandbox
        sandbox = ToggleLabel(trans("computer_use.sandbox"), parent=self.window)
        sandbox.box.setToolTip(trans("computer_use.sandbox.tooltip"))
        sandbox.box.toggled.connect(self.on_sandbox_toggled)
        nodes['computer_sandbox'] = sandbox

        env_layout = QHBoxLayout()
        env_layout.addWidget(label, 0)
        env_layout.addWidget(cbox, 1)

        layout = QVBoxLayout()
        layout.addLayout(env_layout)
        layout.addWidget(sandbox, 0)
        layout.setContentsMargins(2, 5, 5, 5)
        return layout