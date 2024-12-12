#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.09 03:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget, QSizePolicy, QHBoxLayout

from pygpt_net.ui.widget.textarea.name import NameInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.audio.input_button import VoiceControlButton
from pygpt_net.utils import trans

from .agent import Agent
from .agent_llama import AgentLlama
from .image import Image
from .indexes import Indexes
from .vision import Vision
from ...widget.option.toggle_label import ToggleLabel


class Footer:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.agent = Agent(window)
        self.agent_llama = AgentLlama(window)
        self.image = Image(window)
        self.indexes = Indexes(window)
        self.vision = Vision(window)

    def setup(self) -> QWidget:
        """
        Setup footer

        :return: QHBoxLayout
        """
        # AI and users names
        # names_layout = QHBoxLayout()
        # names_layout.addLayout(self.setup_name_input('preset.ai_name', trans("toolbox.name.ai")))
        # names_layout.addLayout(self.setup_name_input('preset.user_name', trans("toolbox.name.user")))

        # bottom
        option = dict(self.window.controller.settings.editor.get_options()["temperature"])
        self.window.ui.nodes['temperature.label'] = QLabel(trans("toolbox.temperature.label"))
        self.window.ui.config['global']['current_temperature'] = \
            OptionSlider(self.window, 'global', 'current_temperature', option)
        self.window.ui.add_hook("update.global.current_temperature", self.window.controller.mode.hook_global_temperature)

        # voice control btn
        self.window.ui.nodes['voice.control.btn'] = VoiceControlButton(self.window)
        self.window.ui.nodes['voice.control.btn'].setVisible(False)

        # per mode options
        rows = QVBoxLayout()
        # rows.addWidget(self.window.ui.nodes['temperature.label'])
        # rows.addWidget(self.window.ui.config['global']['current_temperature'])
        rows.addWidget(self.agent.setup())
        rows.addWidget(self.agent_llama.setup())
        rows.addWidget(self.image.setup())
        # rows.addWidget(self.vision.setup())
        rows.addWidget(self.indexes.setup_options())
        rows.addWidget(self.window.ui.nodes['voice.control.btn'])
        rows.setContentsMargins(2, 0, 0, 0)

        self.window.ui.nodes['layout.split'] = ToggleLabel(trans('layout.split'), label_position="left",
                                                          icon=":/icons/split_screen.svg")
        self.window.ui.nodes['layout.split'].box.stateChanged.connect(
            lambda: self.window.controller.ui.tabs.toggle_split_screen(self.window.ui.nodes['layout.split'].box.isChecked())
        )
        split_layout = QHBoxLayout()

        split_layout.addWidget(QLabel(""))
        split_layout.addStretch(1)
        split_layout.addWidget(self.window.ui.nodes['layout.split'])
        split_layout.setContentsMargins(5, 0, 15, 0)
        split_widget = QWidget()
        split_widget.setLayout(split_layout)
        rows.addWidget(split_widget)

        # logo
        logo_button = self.setup_logo()

        # bottom (options and logo)
        # bottom = QHBoxLayout()
        # bottom.addLayout(rows, 80)
        # bottom.addWidget(logo_button, 20)
        # bottom.setStretchFactor(logo_button, 1)
        # bottom.setAlignment(logo_button, Qt.AlignRight | Qt.AlignBottom)
        # bottom_widget = QWidget()
        # bottom_widget.setLayout(bottom)

        # layout rows
        # layout = QVBoxLayout()
        # layout.addLayout(names_layout)
        # layout.addWidget(bottom_widget)

        widget = QWidget()
        widget.setLayout(rows)

        return widget

    def setup_name_input(self, id: str, title: str) -> QVBoxLayout:
        """
        Setup name input

        :param id: ID of the input
        :param title: Title of the input
        :return: QVBoxLayout
        """
        label_key = 'toolbox.' + id + '.label'
        self.window.ui.nodes[label_key] = QLabel(title)
        self.window.ui.nodes[id] = NameInput(self.window, id)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(self.window.ui.nodes[id])

        return layout

    def setup_logo(self) -> QPushButton:
        """
        Setup logo

        :return: QPushButton
        """
        path = os.path.abspath(os.path.join(self.window.core.config.get_app_path(), 'data', 'logo.png'))

        button = QPushButton()
        button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        button.setIcon(QIcon(path))
        button.setIconSize(QSize(100, 28))
        button.setFlat(True)
        button.clicked.connect(lambda: self.window.controller.dialogs.info.goto_website())

        return button
