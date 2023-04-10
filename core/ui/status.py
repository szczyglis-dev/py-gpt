#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QLabel, QHBoxLayout

from core.utils import trans


class Status:
    def __init__(self, window=None):
        """
        Input

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """
        Setup status

        :return: QHBoxLayout
        """
        self.window.data['status'] = QLabel(trans('status.started'))
        layout = QHBoxLayout()
        layout.addWidget(self.window.data['status'])
        return layout
