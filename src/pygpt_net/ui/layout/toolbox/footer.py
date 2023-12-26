#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QSize
from PySide6.QtGui import Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget, QSizePolicy

from pygpt_net.ui.layout.toolbox.image import Image
from pygpt_net.ui.layout.toolbox.vision import Vision
from pygpt_net.ui.widget.textarea.name import NameInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.utils import trans


class Footer:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.image = Image(window)
        self.vision = Vision(window)

    def setup(self):
        """
        Setup footer

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        # AI and users names
        names_layout = QHBoxLayout()
        names_layout.addLayout(self.setup_name_input('preset.ai_name', trans("toolbox.name.ai")))
        names_layout.addLayout(self.setup_name_input('preset.user_name', trans("toolbox.name.user")))

        # bottom
        self.window.ui.nodes['temperature.label'] = QLabel(trans("toolbox.temperature.label"))
        self.window.ui.config_option['current_temperature'] = OptionSlider(self.window, 'current_temperature',
                                                                           '', 0, 200,
                                                                           1, 100, False)

        # per mode options
        rows = QVBoxLayout()
        rows.addWidget(self.window.ui.nodes['temperature.label'])
        rows.addWidget(self.window.ui.config_option['current_temperature'])
        rows.addWidget(self.image.setup())
        rows.addWidget(self.vision.setup())

        # logo
        logo_button = self.setup_logo()

        # bottom (options and logo)
        bottom = QHBoxLayout()
        bottom.addLayout(rows, 80)
        bottom.addWidget(logo_button, 20)
        bottom.setStretchFactor(logo_button, 1)
        bottom.setAlignment(logo_button, Qt.AlignRight | Qt.AlignBottom)
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom)

        # layout rows
        layout = QVBoxLayout()
        layout.addLayout(names_layout)
        layout.addWidget(bottom_widget)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_name_input(self, id, title):
        """
        Setup name input

        :param id: ID of the input
        :param title: Title of the input
        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        label_key = 'toolbox.' + id + '.label'
        self.window.ui.nodes[label_key] = QLabel(title)
        self.window.ui.nodes[id] = NameInput(self.window, id)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(self.window.ui.nodes[id])

        return layout

    def setup_logo(self):
        """
        Setup logo

        :return: QPushButton
        :rtype: QPushButton
        """
        path = os.path.abspath(os.path.join(self.window.core.config.get_root_path(), 'data', 'logo.png'))

        button = QPushButton()
        button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        button.setIcon(QIcon(path))
        button.setIconSize(QSize(100, 28))
        button.setFlat(True)
        button.clicked.connect(lambda: self.window.controller.info.goto_website())

        return button
