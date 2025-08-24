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
        ui = self.window.ui
        nodes = ui.nodes

        # mode / model
        tip = HelpLabel(trans('tip.toolbox.mode'), self.window)
        tip.setAlignment(Qt.AlignCenter)
        nodes['tip.toolbox.mode'] = tip

        # presets / assistants
        toolbox_mode = QWidget(self.window)
        layout = QVBoxLayout(toolbox_mode)
        layout.addWidget(self.mode.setup())  # modes
        layout.addWidget(self.model.setup())  # models
        layout.addWidget(tip)
        layout.addWidget(self.presets.setup(), 1)  # presets / agents
        layout.addWidget(self.assistants.setup(), 1)  # assistants
        layout.setContentsMargins(0, 0, 0, 0)

        toolbox_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        nodes['toolbox.mode'] = toolbox_mode
        nodes['toolbox.mode.layout'] = layout

        bottom_widget = QWidget(self.window)
        bottom = QVBoxLayout(bottom_widget)
        bottom.addWidget(self.prompt.setup())
        bottom.addWidget(self.footer.setup())
        bottom.setContentsMargins(0, 0, 0, 0)

        # rows
        splitter = QSplitter(Qt.Vertical, self.window)
        splitter.addWidget(toolbox_mode)  # mode/model
        splitter.addWidget(bottom_widget)  # system prompt, footer (names, temp, logo, etc.)
        ui.splitters['toolbox'] = splitter

        return splitter