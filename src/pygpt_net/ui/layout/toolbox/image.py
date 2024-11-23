#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 19:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QCheckBox

from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.utils import trans


class Image:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup image

        :return: QWidget
        :rtype: QWidget
        """
        # img variants
        option = {
            "type": "int",
            "slider": True,
            "label": "img_variants",
            "min": 1,
            "max": 4,
            "step": 1,
            "value": 1,
            "multiplier": 1,
        }
        self.window.ui.nodes['img_variants.label'] = QLabel(trans("toolbox.img_variants.label"))
        self.window.ui.config['global']['img_variants'] = \
            OptionSlider(self.window, 'global', 'img_variants', option)

        # img raw
        self.window.ui.config['global']['img_raw'] = QCheckBox(trans("img.raw"))
        self.window.ui.config['global']['img_raw'].stateChanged.connect(
            lambda:
            self.window.controller.chat.common.img_toggle_raw(self.window.ui.config['global']['img_raw'].isChecked()))

        # label
        label = QLabel(trans("toolbox.img_variants.label"))

        # options
        cols = QHBoxLayout()
        cols.addWidget(self.window.ui.config['global']['img_raw'])
        cols.addWidget(self.window.ui.config['global']['img_variants'])

        # rows
        rows = QVBoxLayout()
        rows.addWidget(label)
        rows.addLayout(cols)
        rows.setContentsMargins(2, 5, 5, 5)

        self.window.ui.nodes['dalle.options'] = QWidget()
        self.window.ui.nodes['dalle.options'].setLayout(rows)
        self.window.ui.nodes['dalle.options'].setContentsMargins(2, 0, 0, 0)

        return self.window.ui.nodes['dalle.options']
