#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.vision.camera import VideoContainer


class Video:
    def __init__(self, window=None):
        """
        Context list UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> VideoContainer:
        """
        Setup video preview
        :return: VideoContainer
        :rtype: VideoContainer
        """
        self.window.ui.nodes['video.preview'] = VideoContainer(self.window)
        self.window.ui.nodes['video.preview'].setVisible(False)

        return self.window.ui.nodes['video.preview']
