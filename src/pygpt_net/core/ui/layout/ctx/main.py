#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 18:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .ctx_list import CtxList
from .video import Video


class CtxMain:
    def __init__(self, window=None):
        """
        Context list UI

        :param window: Window instance
        """
        self.window = window
        self.ctx_list = CtxList(window)
        self.video = Video(window)

    def setup(self):
        """
        Setup layout

        :return: QWidget
        :rtype: QWidget
        """
        ctx = self.ctx_list.setup()
        video = self.video.setup()

        layout = QVBoxLayout()
        layout.addWidget(ctx)
        layout.addWidget(video)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

