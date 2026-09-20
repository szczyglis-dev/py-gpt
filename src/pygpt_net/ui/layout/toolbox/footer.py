#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 13:55:00                  #
# ================================================== #

import os

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget, QSizePolicy, QHBoxLayout

from pygpt_net.ui.widget.textarea.name import NameInput
from pygpt_net.ui.widget.audio.input_button import VoiceControlButton
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans

from .agent import Agent
from .agent_llama import AgentLlama
from .audio import Audio
from .computer_env import ComputerEnv
from .image import Image
from .indexes import Indexes
from .vision import Vision
from .video import Video
from .raw import Raw
from .split import Split


class Footer:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.agent = Agent(window)
        self.agent_llama = AgentLlama(window)
        self.audio = Audio(window)
        self.env = ComputerEnv(window)
        self.image = Image(window)
        self.indexes = Indexes(window)
        self.vision = Vision(window)
        self.video = Video(window)
        self.raw = Raw(window)
        self.split = Split(window)
        # Logical hover sections exposed to ToolboxMain. Every direct footer
        # block, including Split screen, is independent.
        self.hover_sections = []

    def setup(self) -> QWidget:
        """
        Setup footer

        :return: QHBoxLayout
        """
        # voice control btn
        self.window.ui.nodes['voice.control.btn'] = VoiceControlButton(self.window)
        self.window.ui.nodes['voice.control.btn'].setVisible(False)

        # Per-mode options. Each direct block is an independent hover section
        # instead of treating the complete footer as one large section.
        sections = [
            self.agent.setup(),
            self.agent_llama.setup(),
            self.raw.setup(),
            self.image.setup(),
            self.video.setup(),
            self.indexes.setup_options(),
            self.env.setup(),
            self.window.ui.nodes['voice.control.btn'],
            self.audio.setup(),
            self.split.setup(),
        ]

        widget = QWidget(self.window)
        rows = QVBoxLayout(widget)
        for section in sections:
            rows.addWidget(section)

        rows.setContentsMargins(2, 0, 0, 0)
        self.hover_sections = sections

        return widget

    def setup_name_input(self, id: str, title: str) -> QVBoxLayout:
        """
        Setup name input

        :param id: ID of the input
        :param title: Title of the input
        :return: QVBoxLayout
        """
        label_key = 'toolbox.' + id + '.label'
        self.window.ui.nodes[label_key] = QLabel(title, self.window)
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

        button = QPushButton(self.window)
        button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        button.setIcon(QIcon(path))
        button.setIconSize(QSize(100, 28))
        button.setFlat(True)
        button.clicked.connect(self.window.controller.dialogs.info.goto_website)

        return button