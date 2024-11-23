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

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget, QSizePolicy

from pygpt_net.ui.layout.toolbox.assistants import Assistants
from pygpt_net.ui.layout.toolbox.indexes import Indexes
from pygpt_net.ui.layout.toolbox.mode import Mode
from pygpt_net.ui.layout.toolbox.model import Model
from pygpt_net.ui.layout.toolbox.presets import Presets
from pygpt_net.ui.layout.toolbox.prompt import Prompt
from pygpt_net.ui.layout.toolbox.footer import Footer
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans


class ToolboxMain:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.assistants = Assistants(window)
        self.indexes = Indexes(window)
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
        self.window.ui.nodes['tip.toolbox.mode'] = HelpLabel(trans('tip.toolbox.mode'), self.window)
        self.window.ui.nodes['tip.toolbox.mode'].setAlignment(Qt.AlignCenter)

        # presets / assistants
        self.window.ui.nodes['toolbox.mode.layout'] = QVBoxLayout()
        self.window.ui.nodes['toolbox.mode.layout'].addWidget(self.mode.setup())  # modes
        self.window.ui.nodes['toolbox.mode.layout'].addWidget(self.model.setup())  # models
        self.window.ui.nodes['toolbox.mode.layout'].addWidget(self.window.ui.nodes['tip.toolbox.mode'])
        self.window.ui.nodes['toolbox.mode.layout'].addWidget(self.presets.setup(), 1)  # presets / agents
        self.window.ui.nodes['toolbox.mode.layout'].addWidget(self.assistants.setup(), 1)  # assistants
        self.window.ui.nodes['toolbox.mode.layout'].setContentsMargins(0, 0, 0, 0)

        self.window.ui.nodes['toolbox.mode'] = QWidget()
        self.window.ui.nodes['toolbox.mode'].setLayout(self.window.ui.nodes['toolbox.mode.layout'])
        self.window.ui.nodes['toolbox.mode'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        bottom = QVBoxLayout()
        bottom.addWidget(self.prompt.setup())
        bottom.addWidget(self.footer.setup())
        bottom.setContentsMargins(0, 0, 0, 0)

        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom)

        # rows
        self.window.ui.splitters['toolbox'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['toolbox'].addWidget(self.window.ui.nodes['toolbox.mode'])  # mode/model
        self.window.ui.splitters['toolbox'].addWidget(bottom_widget)  # system prompt, footer (names, temp, logo, etc.)

        return self.window.ui.splitters['toolbox']
