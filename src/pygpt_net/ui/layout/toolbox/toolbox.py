#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.03 14:25:00                  #
# ================================================== #

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget, QSizePolicy

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans

from .assistants import Assistants
from .indexes import Indexes
from .mode import Mode
from .model import Model
from .presets import Presets
from .prompt import Prompt
from .footer import Footer

class ToolboxMain:
    MIN_WIDTH = 256

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

        # The toolbox must remain horizontally shrinkable. Some mode-specific
        # controls have wide size hints (or are only visible in selected modes),
        # so using the default horizontal policy here would let those hints raise
        # the effective minimum width of the whole right pane.
        toolbox_mode.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        toolbox_mode.setMinimumWidth(0)
        nodes['toolbox.mode'] = toolbox_mode
        nodes['toolbox.mode.layout'] = layout

        bottom_widget = QWidget(self.window)
        bottom_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        bottom_widget.setMinimumWidth(0)
        bottom = QVBoxLayout(bottom_widget)
        bottom.addWidget(self.prompt.setup())
        bottom.addWidget(self.footer.setup())
        bottom.setContentsMargins(0, 0, 0, 0)

        # rows
        splitter = QSplitter(Qt.Vertical, self.window)
        # Keep one stable minimum width regardless of which mode-specific
        # widgets are currently visible. QSizePolicy.Ignored makes the parent
        # splitter ignore changing child size hints while the explicit minimum
        # below still prevents collapsing the toolbox too far.
        splitter.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        splitter.setMinimumWidth(self.MIN_WIDTH)
        splitter.addWidget(toolbox_mode)  # mode/model
        splitter.addWidget(bottom_widget)  # system prompt, footer (names, temp, logo, etc.)
        ui.splitters['toolbox'] = splitter

        return splitter