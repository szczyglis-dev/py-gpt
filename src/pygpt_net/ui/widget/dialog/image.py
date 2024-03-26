#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.26 15:00:00                  #
# ================================================== #

from .base import BaseDialog


class ImageDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Image dialog

        :param window: main window
        :param id: info window id
        """
        super(ImageDialog, self).__init__(window, id)
        self.window = window
        self.id = id
