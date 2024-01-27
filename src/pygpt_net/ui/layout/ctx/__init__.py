#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 11:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pygpt_net.ui.layout.ctx.search_input import SearchInput
from pygpt_net.ui.layout.ctx.ctx_list import CtxList
from pygpt_net.ui.layout.ctx.video import Video
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans


class CtxMain:
    def __init__(self, window=None):
        """
        Context list UI

        :param window: Window instance
        """
        self.window = window
        self.search_input = SearchInput(window)
        self.ctx_list = CtxList(window)
        self.video = Video(window)

    def setup(self) -> QWidget:
        """
        Setup layout

        :return: QWidget
        """
        ctx = self.ctx_list.setup()
        video = self.video.setup()
        search_input = self.search_input.setup()

        self.window.ui.nodes['tip.toolbox.ctx'] = HelpLabel(trans('tip.toolbox.ctx'), self.window)

        layout = QVBoxLayout()
        layout.addWidget(ctx)

        layout.addWidget(self.window.ui.nodes['tip.toolbox.ctx'])
        layout.addWidget(search_input)
        layout.addWidget(video)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

