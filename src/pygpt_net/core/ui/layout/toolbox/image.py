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

from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QCheckBox

from pygpt_net.core.ui.widget.option.slider import OptionSlider
from pygpt_net.core.utils import trans


class Image:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup image

        :return: QWidget
        :rtype: QWidget
        """
        # img variants
        self.window.ui.nodes['img_variants.label'] = QLabel(trans("toolbox.img_variants.label"))
        self.window.ui.config_option['img_variants'] = OptionSlider(self.window, 'img_variants',
                                                                    '', 1, 4,
                                                                    1, 1, False)

        # img raw
        self.window.ui.config_option['img_raw'] = QCheckBox(trans("img.raw"))
        self.window.ui.config_option['img_raw'].stateChanged.connect(
            lambda: self.window.controller.image.toggle_raw(self.window.ui.config_option['img_raw'].isChecked()))

        # label
        label = QLabel(trans("toolbox.img_variants.label"))

        # options
        cols = QHBoxLayout()
        cols.addWidget(self.window.ui.config_option['img_raw'])
        cols.addWidget(self.window.ui.config_option['img_variants'])

        # rows
        rows = QVBoxLayout()
        rows.addWidget(label)
        rows.addLayout(cols)

        self.window.ui.nodes['dalle.options'] = QWidget()
        self.window.ui.nodes['dalle.options'].setLayout(rows)
        self.window.ui.nodes['dalle.options'].setContentsMargins(0, 0, 0, 0)

        return self.window.ui.nodes['dalle.options']
