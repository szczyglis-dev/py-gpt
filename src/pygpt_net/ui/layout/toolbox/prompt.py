#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.15 15:00:00                  #
# ================================================== #

from PySide6.QtGui import Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QCheckBox, QSizePolicy

from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.option.prompt import PromptTextarea
from pygpt_net.utils import trans
import pygpt_net.icons_rc

class Prompt:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup system prompt

        :return: QWidget
        """
        # cmd enable/disable
        self.window.ui.nodes['cmd.enabled'] = QCheckBox(trans('cmd.enabled'))
        self.window.ui.nodes['cmd.enabled'].stateChanged.connect(
            lambda: self.window.controller.chat.common.toggle_cmd(self.window.ui.nodes['cmd.enabled'].isChecked())
        )
        self.window.ui.nodes['cmd.enabled'].setToolTip(trans('cmd.tip'))

        # label
        self.window.ui.nodes['toolbox.prompt.label'] = TitleLabel(trans("toolbox.prompt"))

        # clear
        self.window.ui.nodes['preset.clear'] = QPushButton(QIcon(":/icons/close.svg"),"")
        self.window.ui.nodes['preset.clear'].clicked.connect(
            lambda: self.window.controller.presets.clear())

        # use
        self.window.ui.nodes['preset.use'] = QPushButton(trans('preset.use'))
        self.window.ui.nodes['preset.use'].clicked.connect(
            lambda: self.window.controller.presets.use())
        self.window.ui.nodes['preset.use'].setVisible(False)

        # cols
        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['toolbox.prompt.label'])
        header.addWidget(self.window.ui.nodes['cmd.enabled'])
        header.addStretch(1)
        header.addWidget(self.window.ui.nodes['preset.use'], alignment=Qt.AlignRight)
        header.addWidget(self.window.ui.nodes['preset.clear'], alignment=Qt.AlignRight)

        # prompt
        option = self.window.controller.presets.editor.get_option('prompt')
        self.window.ui.nodes['preset.prompt'] = PromptTextarea(self.window, 'preset', 'prompt', option)
        self.window.ui.nodes['preset.prompt'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.window.ui.nodes['tip.toolbox.prompt'] = HelpLabel(trans('tip.toolbox.prompt'), self.window)

        # rows
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.ui.nodes['preset.prompt'])
        layout.addWidget(self.window.ui.nodes['tip.toolbox.prompt'])
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return widget
