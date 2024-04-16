#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .widgets import IdxBrowser


class BrowseTab:
    def __init__(self, window=None):
        """
        Tab: Browse

        :param window: Window instance
        """
        self.window = window
        self.browser = None

    def setup(self):
        """
        Setup tab widget
        """
        # idx db browser
        self.browser = IdxBrowser(self.window)
        self.window.ui.nodes['tool.indexer.browser'] = self.browser

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.browser)

        widget = QWidget()
        widget.setLayout(layout)

        return widget
