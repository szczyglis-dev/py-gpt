#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.24 22:00:00                  #
# ================================================== #

from PySide6.QtGui import Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QCheckBox, QSizePolicy

from pygpt_net.ui.widget.anims.toggles import AnimToggle
from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.option.prompt import PromptTextarea
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
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
        self.window.ui.nodes['cmd.enabled'] = ToggleLabel(trans('cmd.enabled'), label_position="left",icon = ":/icons/build.svg")
        self.window.ui.nodes['cmd.enabled'].box.stateChanged.connect(
            lambda: self.window.controller.chat.common.toggle_cmd(self.window.ui.nodes['cmd.enabled'].box.isChecked())
        )
        self.window.ui.nodes['cmd.enabled'].box.setToolTip(trans('cmd.tip'))
        self.window.ui.nodes['cmd.enabled'].box.setIcon(QIcon(":/icons/add.svg"))

        # label
        self.window.ui.nodes['toolbox.prompt.label'] = TitleLabel(trans("toolbox.prompt"))

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.window.ui.nodes['toolbox.prompt.label'])
        header_layout.addStretch(1)
        header_layout.addWidget(self.window.ui.nodes['cmd.enabled'])
        header_layout.setContentsMargins(5, 0, 10, 0)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)

        # clear
        """
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
        header.addWidget(header_widget)
        #header.addStretch(1)
        #header.addWidget(self.window.ui.nodes['preset.use'], alignment=Qt.AlignRight)
        #header.addWidget(self.window.ui.nodes['preset.clear'], alignment=Qt.AlignRight)
        """

        # prompt
        option = self.window.controller.presets.editor.get_option('prompt')
        self.window.ui.nodes['preset.prompt'] = PromptTextarea(self.window, 'preset', 'prompt', option)
        self.window.ui.nodes['preset.prompt'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.window.ui.nodes['tip.toolbox.prompt'] = HelpLabel(trans('tip.toolbox.prompt'), self.window)
        self.window.ui.nodes['tip.toolbox.prompt'].setAlignment(Qt.AlignCenter)

        # rows
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes['preset.prompt'])
        layout.addWidget(self.window.ui.nodes['tip.toolbox.prompt'])
        layout.setContentsMargins(2, 5, 5, 5)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return widget
