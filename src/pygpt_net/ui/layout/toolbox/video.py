#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.03 14:25:00                  #
# ================================================== #

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy

from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.input import OptionInput
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


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

        container = QWidget(parent=self.window)
        container.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        container.setMinimumWidth(0)
        ui.nodes['video.options'] = container

        option_ratio = self.window.core.video.get_aspect_ratio_option()
        option_resolution = self.window.core.video.get_resolution_option()
        option_duration = self.window.core.video.get_duration_option()

        conf_global['video.aspect_ratio'] = OptionCombo(self.window, 'global', 'video.aspect_ratio', option_ratio)
        conf_global['video.aspect_ratio'].setToolTip(trans('settings.video.aspect_ratio.desc'))
        conf_global['video.resolution'] = OptionCombo(self.window, 'global', 'video.resolution', option_resolution)
        conf_global['video.resolution'].setToolTip(trans('settings.video.resolution.desc'))
        conf_global['video.duration'] = OptionInput(self.window, 'global', 'video.duration', option_duration)
        conf_global['video.duration'].setToolTip(trans('settings.video.duration.desc'))

        # These controls share one row; hard minimums here used to propagate
        # into the toolbox and widen the whole right pane in video mode.
        conf_global['video.aspect_ratio'].setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        conf_global['video.resolution'].setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        conf_global['video.duration'].setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        conf_global['video.aspect_ratio'].setMinimumWidth(0)
        conf_global['video.resolution'].setMinimumWidth(0)
        conf_global['video.duration'].setMinimumWidth(0)

        conf_global['video.remix'] = ToggleLabel(trans("video.remix"), parent=self.window)
        conf_global['video.remix'].box.setToolTip(trans("video.remix.tooltip"))
        conf_global['video.remix'].box.toggled.connect(self.window.controller.media.toggle_remix_video)

        cols = QHBoxLayout()
        cols.addWidget(conf_global['video.resolution'], 2)
        cols.addWidget(conf_global['video.aspect_ratio'], 2)
        cols.addWidget(conf_global['video.duration'], 1)
        cols.setContentsMargins(2, 5, 5, 5)

        rows = QVBoxLayout()
        rows.addLayout(cols)
        rows.addWidget(conf_global['video.remix'])
        rows.setContentsMargins(0, 0, 0, 0)

        container.setLayout(rows)
        container.setContentsMargins(2, 0, 0, 10)
        container.setFixedHeight(90)

        return container