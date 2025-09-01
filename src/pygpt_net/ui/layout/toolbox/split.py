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

from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


class Split:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup split screen

        :return: QWidget
        :rtype: QWidget
        """
        self.window.ui.nodes['layout.split'] = ToggleLabel(trans('layout.split'), label_position="left",
                                                           icon=":/icons/split_screen.svg",
                                                           parent=self.window)
        self.window.ui.nodes['layout.split'].box.toggled.connect(
            self.window.controller.ui.tabs.toggle_split_screen
        )
        split_widget = QWidget(self.window)
        split_layout = QHBoxLayout(split_widget)

        split_layout.addWidget(QLabel("", split_widget))
        split_layout.addStretch(1)
        split_layout.addWidget(self.window.ui.nodes['layout.split'])
        split_layout.setContentsMargins(5, 0, 15, 0)

        return split_widget