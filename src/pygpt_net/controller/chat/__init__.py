#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 21:00:00                  #
# ================================================== #

from .common import Common
from .files import Files
from .image import Image
from .input import Input
from .output import Output
from .render import Render
from .text import Text


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

    def setup(self):
        """Setup"""
        self.common.setup()
