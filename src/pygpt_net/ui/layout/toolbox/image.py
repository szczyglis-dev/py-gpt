#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.30 22:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout

from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.input import OptionInput
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
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
        option = {
            "type": "int",
            "label": "img_variants",
            "min": 1,
            "max": 4,
            "value": 1,
        }

        ui = self.window.ui
        conf_global = ui.config['global']

        container = QWidget(parent=self.window)
        ui.nodes['dalle.options'] = container

        conf_global['img_variants'] = OptionInput(self.window, 'global', 'img_variants', option)
        conf_global['img_variants'].setToolTip(trans("toolbox.img_variants.label"))

        option_resolutions = self.window.core.image.get_resolution_option()
        conf_global['img_resolution'] = OptionCombo(self.window, 'global', 'img_resolution', option_resolutions)
        conf_global['img_resolution'].setMinimumWidth(160)

        conf_global['img.remix'] = ToggleLabel(trans("img.remix"), parent=self.window)
        conf_global['img.remix'].box.setToolTip(trans("img.remix.tooltip"))
        conf_global['img.remix'].box.toggled.connect(self.window.controller.media.toggle_remix_image)

        cols = QHBoxLayout()
        cols.addWidget(conf_global['img_resolution'], 3)
        cols.addWidget(conf_global['img_variants'], 1)
        cols.setContentsMargins(2, 5, 5, 5)

        rows = QVBoxLayout()
        rows.addLayout(cols)
        rows.addWidget(conf_global['img.remix'])
        rows.setContentsMargins(2, 5, 5, 5)

        container.setLayout(rows)
        container.setContentsMargins(2, 0, 0, 10)
        container.setFixedHeight(100)

        return container