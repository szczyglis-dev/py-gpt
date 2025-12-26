#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.26 12:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QWidget, QHBoxLayout

from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.input import OptionInput


class Video:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup video

        :return: QWidget
        :rtype: QWidget
        """
        ui = self.window.ui
        conf_global = ui.config['global']

        container = QWidget()
        ui.nodes['video.options'] = container

        option_ratio = self.window.core.video.get_aspect_ratio_option()
        option_resolution = self.window.core.video.get_resolution_option()
        option_duration = self.window.core.video.get_duration_option()

        conf_global['video.aspect_ratio'] = OptionCombo(self.window, 'global', 'video.aspect_ratio', option_ratio)
        conf_global['video.resolution'] = OptionCombo(self.window, 'global', 'video.resolution', option_resolution)
        conf_global['video.duration'] = OptionInput(self.window, 'global', 'video.duration', option_duration)

        rows = QHBoxLayout()
        rows.addWidget(conf_global['video.resolution'], 2)
        rows.addWidget(conf_global['video.aspect_ratio'], 2)
        rows.addWidget(conf_global['video.duration'], 1)
        rows.setContentsMargins(2, 5, 5, 5)

        container.setLayout(rows)
        container.setContentsMargins(2, 0, 0, 0)

        return container