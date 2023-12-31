#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QSplitter

from pygpt_net.ui.layout.toolbox.assistants import Assistants
from pygpt_net.ui.layout.toolbox.mode import Mode
from pygpt_net.ui.layout.toolbox.model import Model
from pygpt_net.ui.layout.toolbox.presets import Presets
from pygpt_net.ui.layout.toolbox.prompt import Prompt
from pygpt_net.ui.layout.toolbox.footer import Footer


class ToolboxMain:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.assistants = Assistants(window)
        self.footer = Footer(window)
        self.mode = Mode(window)
        self.model = Model(window)
        self.presets = Presets(window)
        self.prompt = Prompt(window)

    def setup(self) -> QSplitter:
        """
        Setup toolbox

        :return: QSplitter
        :rtype: QSplitter
        """
        # mode / model
        self.window.ui.splitters['toolbox.mode'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['toolbox.mode'].addWidget(self.mode.setup())  # modes
        self.window.ui.splitters['toolbox.mode'].addWidget(self.model.setup())  # models

        # presets / assistants
        self.window.ui.splitters['toolbox.presets'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['toolbox.presets'].addWidget(self.presets.setup())  # prompts
        self.window.ui.splitters['toolbox.presets'].addWidget(self.assistants.setup())  # assistants

        # rows
        self.window.ui.splitters['toolbox'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['toolbox'].addWidget(self.window.ui.splitters['toolbox.mode'])  # mode/model
        self.window.ui.splitters['toolbox'].addWidget(self.window.ui.splitters['toolbox.presets'])  # presets/assists.
        self.window.ui.splitters['toolbox'].addWidget(self.prompt.setup())  # system prompt
        self.window.ui.splitters['toolbox'].addWidget(self.footer.setup())  # footer (names, temp, logo, etc.)

        return self.window.ui.splitters['toolbox']
