#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 09:55:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QCheckBox

from pygpt_net.ui.widget.element.labels import ElideLabel
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
        nodes = self.window.ui.nodes
        camera = self.window.controller.camera

        nodes['vision.capture.options'] = QWidget()
        options = nodes['vision.capture.options']

        nodes['vision.capture.enable'] = QCheckBox(trans("vision.capture.enable"), parent=options)
        nodes['vision.capture.enable'].toggled.connect(camera.toggle)
        nodes['vision.capture.enable'].setToolTip(trans('vision.capture.enable.tooltip'))

        nodes['vision.capture.auto'] = QCheckBox(trans("vision.capture.auto"), parent=options)
        nodes['vision.capture.auto'].toggled.connect(camera.toggle_auto)
        nodes['vision.capture.auto'].setToolTip(trans('vision.capture.auto.tooltip'))

        nodes['vision.capture.label'] = ElideLabel(trans('vision.capture.options.title'), window=options)

        cols = QHBoxLayout()
        cols.addWidget(nodes['vision.capture.enable'])
        cols.addWidget(nodes['vision.capture.auto'])

        rows = QVBoxLayout()
        rows.addWidget(nodes['vision.capture.label'])
        rows.addLayout(cols)

        options.setLayout(rows)
        options.setContentsMargins(0, 0, 0, 0)

        return options