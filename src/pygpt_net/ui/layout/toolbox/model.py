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
        self.label_key = f'{self.id}.label'

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
        nodes = self.window.ui.nodes

        label = TitleLabel(trans("toolbox.model.label"))
        label.setContentsMargins(5, 0, 0, 0)
        nodes[self.label_key] = label

        combo = ModelCombo(self.window, self.id)
        nodes[self.id] = combo

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(combo)
        layout.addStretch()
        layout.setContentsMargins(2, 5, 5, 5)

        return layout