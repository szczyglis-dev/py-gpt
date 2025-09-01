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

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pygpt_net.ui.widget.option.combo import OptionCombo


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

        option_resolutions = self.window.core.video.get_aspect_ratio_option()
        conf_global['video.aspect_ratio'] = OptionCombo(self.window, 'global', 'video.aspect_ratio', option_resolutions)

        rows = QVBoxLayout()
        rows.addWidget(conf_global['video.aspect_ratio'])
        rows.setContentsMargins(2, 5, 5, 5)

        container.setLayout(rows)
        container.setContentsMargins(2, 0, 0, 0)

        return container