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

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QCheckBox

from pygpt_net.utils import trans


class Raw:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup media raw

        :return: QWidget
        :rtype: QWidget
        """
        ui = self.window.ui
        conf_global = ui.config['global']

        container = QWidget()
        ui.nodes['media.raw'] = container

        conf_global['img_raw'] = QCheckBox(trans("img.raw"), parent=container)
        conf_global['img_raw'].toggled.connect(self.window.controller.media.toggle_raw)

        cols = QHBoxLayout()
        cols.addWidget(conf_global['img_raw'])

        rows = QVBoxLayout()
        rows.addLayout(cols)
        rows.setContentsMargins(2, 5, 5, 5)

        container.setLayout(rows)
        container.setContentsMargins(2, 0, 0, 0)

        return container