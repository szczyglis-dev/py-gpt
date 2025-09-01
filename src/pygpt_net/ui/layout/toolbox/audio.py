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

from PySide6.QtWidgets import QHBoxLayout, QWidget

from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


class Audio:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup audio

        :return: QWidget
        :rtype: QWidget
        """
        self.window.ui.nodes['audio.auto_turn'] = ToggleLabel(trans('audio.auto_turn'), label_position="left",
                                                              icon=":/icons/voice.svg",
                                                              parent=self.window)
        self.window.ui.nodes['audio.auto_turn'].box.toggled.connect(
            self.window.controller.audio.toggle_auto_turn
        )
        self.window.ui.nodes['audio.loop'] = ToggleLabel(trans('audio.loop'), label_position="left",
                                                              parent=self.window)
        self.window.ui.nodes['audio.loop'].box.toggled.connect(
            self.window.controller.audio.toggle_loop
        )

        audio_layout = QHBoxLayout()
        audio_layout.addStretch(1)
        audio_layout.addWidget(self.window.ui.nodes['audio.auto_turn'])
        audio_layout.addWidget(self.window.ui.nodes['audio.loop'])
        audio_layout.setContentsMargins(5, 0, 15, 0)

        audio_widget = QWidget()
        audio_widget.setLayout(audio_layout)

        return audio_widget