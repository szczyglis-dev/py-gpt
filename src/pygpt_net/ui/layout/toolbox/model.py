#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 17:00:00                  #
# ================================================== #
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QSizePolicy

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
        self._settings_icon = QIcon(":/icons/settings.svg")

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
        # Ensure combo takes maximum horizontal space
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        nodes[self.id] = combo

        nodes['prompt.model.settings'] = QPushButton(self._settings_icon, "")
        # Configure compact, borderless settings button aligned to the right
        icon_size = 20
        nodes['prompt.model.settings'].setFlat(True)
        nodes['prompt.model.settings'].setStyleSheet("QPushButton { border: none; padding: 0; }")
        nodes['prompt.model.settings'].setIconSize(QSize(icon_size, icon_size))
        nodes['prompt.model.settings'].setFixedSize(icon_size, icon_size)
        nodes['prompt.model.settings'].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        nodes['prompt.model.settings'].setFocusPolicy(Qt.NoFocus)
        nodes['prompt.model.settings'].clicked.connect(self._open_settings)

        model_cols = QHBoxLayout()
        model_cols.addWidget(combo, 1)  # stretch to take remaining space
        model_cols.addWidget(nodes['prompt.model.settings'], alignment=Qt.AlignRight)
        model_cols.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addLayout(model_cols)
        layout.addStretch()
        layout.setContentsMargins(2, 5, 5, 5)

        return layout

    def _open_settings(self):
        self.window.controller.model.editor.open()