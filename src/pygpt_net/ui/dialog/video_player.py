#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.18 03:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout

from pygpt_net.ui.widget.dialog.video_player import VideoPlayerDialog
from pygpt_net.ui.widget.video.player import VideoPlayerWidget
from pygpt_net.utils import trans

class VideoPlayer:
    def __init__(self, window=None):
        """
        Video Player dialog

        :param window: Window instance
        """
        self.window = window
        self.path = None

    def setup(self):
        """Setup video dialog"""
        id = 'video_player'
        self.window.video_player = VideoPlayerWidget(self.window)
        layout = QVBoxLayout()
        layout.addWidget(self.window.video_player)
        self.window.ui.dialog[id] = VideoPlayerDialog(self.window, id)
        self.window.ui.dialog[id].setLayout(layout)
        self.window.ui.dialog[id].setWindowTitle("Video Player")
