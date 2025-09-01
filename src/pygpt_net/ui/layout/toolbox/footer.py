#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.01 23:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget, QSizePolicy, QHBoxLayout

from pygpt_net.ui.widget.textarea.name import NameInput
from pygpt_net.ui.widget.option.slider import OptionSlider
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

    def setup(self) -> QWidget:
        """
        Setup footer

        :return: QHBoxLayout
        """
        # bottom
        option = dict(self.window.controller.settings.editor.get_options()["temperature"])
        self.window.ui.nodes['temperature.label'] = QLabel(trans("toolbox.temperature.label"), self.window)
        self.window.ui.config['global']['current_temperature'] = \
            OptionSlider(self.window, 'global', 'current_temperature', option)
        self.window.ui.add_hook("update.global.current_temperature", self.window.controller.mode.hook_global_temperature)

        # voice control btn
        self.window.ui.nodes['voice.control.btn'] = VoiceControlButton(self.window)
        self.window.ui.nodes['voice.control.btn'].setVisible(False)

        # per mode options
        widget = QWidget(self.window)
        rows = QVBoxLayout(widget)
        rows.addWidget(self.agent.setup())
        rows.addWidget(self.agent_llama.setup())
        rows.addWidget(self.raw.setup())
        rows.addWidget(self.image.setup())
        rows.addWidget(self.video.setup())
        rows.addWidget(self.indexes.setup_options())
        rows.addWidget(self.env.setup())
        rows.addWidget(self.window.ui.nodes['voice.control.btn'])
        rows.addWidget(self.audio.setup())
        rows.addWidget(self.split.setup())

        rows.setContentsMargins(2, 0, 0, 0)

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