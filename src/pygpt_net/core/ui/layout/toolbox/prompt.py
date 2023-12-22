#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 19:00:00                  #
# ================================================== #

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget, QCheckBox

from ...widget.option.textarea import OptionTextarea
from ....utils import trans


class Prompt:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup system prompt

        :return: QWidget
        :rtype: QWidget
        """
        # cmd enable/disable
        self.window.ui.nodes['cmd.enabled'] = QCheckBox(trans('cmd.enabled'))
        self.window.ui.nodes['cmd.enabled'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_cmd(self.window.ui.nodes['cmd.enabled'].isChecked()))

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
        header.addWidget(self.window.ui.nodes['preset.use'], alignment=Qt.AlignRight)
        header.addWidget(self.window.ui.nodes['preset.clear'], alignment=Qt.AlignRight)

        # prompt
        self.window.ui.nodes['preset.prompt'] = OptionTextarea(self.window, 'preset.prompt', True)
        self.window.ui.nodes['preset.prompt'].update_ui = False

        # rows
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.ui.nodes['preset.prompt'])

        widget = QWidget()
        widget.setLayout(layout)

        return widget
