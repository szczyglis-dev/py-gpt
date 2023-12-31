#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QCheckBox

from pygpt_net.utils import trans


class Vision:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup vision

        :return: QWidget
        """
        # enable/disable
        self.window.ui.nodes['vision.capture.enable'] = QCheckBox(trans("vision.capture.enable"))
        self.window.ui.nodes['vision.capture.enable'].stateChanged.connect(
            lambda: self.window.controller.camera.toggle(self.window.ui.nodes['vision.capture.enable'].isChecked()))
        self.window.ui.nodes['vision.capture.enable'].setToolTip(trans('vision.capture.enable.tooltip'))

        # auto
        self.window.ui.nodes['vision.capture.auto'] = QCheckBox(trans("vision.capture.auto"))
        self.window.ui.nodes['vision.capture.auto'].stateChanged.connect(
            lambda: self.window.controller.camera.toggle_auto(self.window.ui.nodes['vision.capture.auto'].isChecked()))
        self.window.ui.nodes['vision.capture.auto'].setToolTip(trans('vision.capture.auto.tooltip'))

        self.window.ui.nodes['vision.capture.label'] = QLabel(trans('vision.capture.options.title'))

        # checkbox options
        cols = QHBoxLayout()
        cols.addWidget(self.window.ui.nodes['vision.capture.enable'])
        cols.addWidget(self.window.ui.nodes['vision.capture.auto'])

        # rows
        rows = QVBoxLayout()
        rows.addWidget(self.window.ui.nodes['vision.capture.label'])
        rows.addLayout(cols)

        # widget
        self.window.ui.nodes['vision.capture.options'] = QWidget()
        self.window.ui.nodes['vision.capture.options'].setLayout(rows)
        self.window.ui.nodes['vision.capture.options'].setContentsMargins(0, 0, 0, 0)

        return self.window.ui.nodes['vision.capture.options']
