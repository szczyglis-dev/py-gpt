#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 02:00:00                  #
# ================================================== #

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget, QCheckBox, QSizePolicy

from pygpt_net.ui.widget.element.help import HelpLabel
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.utils import trans


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
            lambda: self.window.controller.chat.common.toggle_cmd(self.window.ui.nodes['cmd.enabled'].isChecked()))

        # label
        self.window.ui.nodes['toolbox.prompt.label'] = QLabel(trans("toolbox.prompt"))
        self.window.ui.nodes['toolbox.prompt.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        # clear
        self.window.ui.nodes['preset.clear'] = QPushButton(trans('preset.clear'))
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
        self.window.ui.nodes['preset.prompt'] = OptionTextarea(self.window, 'preset', 'prompt', option)
        self.window.ui.nodes['preset.prompt'].real_time = True
        self.window.ui.nodes['preset.prompt'].update_ui = False
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
