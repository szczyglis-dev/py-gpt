#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 19:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QDialog


class ImageDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Image dialog

        :param window: main window
        :param id: info window id
        """
        super(ImageDialog, self).__init__(window)
        self.window = window
        self.id = id
