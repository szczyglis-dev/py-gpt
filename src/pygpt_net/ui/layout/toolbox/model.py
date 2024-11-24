#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.lists.model_combo import ModelCombo
from pygpt_net.utils import trans


class Model:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'prompt.model'

    def setup(self) -> QWidget:
        """
        Setup models

        :return: QWidget7
        """
        widget = QWidget()
        widget.setLayout(self.setup_list())
        return widget

    def setup_list(self) -> QVBoxLayout:
        """
        Setup models list

        :return: QVBoxLayout
        """
        label_key = self.id + '.label'

        self.window.ui.nodes[label_key] = TitleLabel(trans("toolbox.model.label"))
        self.window.ui.nodes[self.id] = ModelCombo(self.window, self.id)

        header_layout = QVBoxLayout()
        header_layout.addWidget(self.window.ui.nodes[label_key])
        header_layout.setContentsMargins(5, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addLayout(header_layout)
        layout.addWidget(self.window.ui.nodes[self.id])
        layout.addStretch()
        layout.setContentsMargins(2, 5, 5, 5)

        return layout
