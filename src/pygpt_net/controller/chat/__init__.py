#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.13 15:00:00                  #
# ================================================== #

from pygpt_net.controller.chat.common import Common
from pygpt_net.controller.chat.files import Files
from pygpt_net.controller.chat.image import Image
from pygpt_net.controller.chat.input import Input
from pygpt_net.controller.chat.output import Output
from pygpt_net.controller.chat.render import Render
from pygpt_net.controller.chat.text import Text
from pygpt_net.controller.chat.vision import Vision


class Chat:
    def __init__(self, window=None):
        """
        Chat input and output controller

        :param window: Window instance
        """
        self.window = window
        self.common = Common(window)
        self.files = Files(window)
        self.image = Image(window)
        self.input = Input(window)
        self.output = Output(window)
        self.render = Render(window)
        self.text = Text(window)
        self.vision = Vision(window)

    def setup(self):
        """Setup"""
        self.common.setup()
