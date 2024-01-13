#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.13 21:00:00                  #
# ================================================== #

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class HelpLabel(QLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setStyleSheet(
            self.window.controller.theme.get_style('text_faded'))
        # self.window.ui.nodes['tip.output.tab.notepad'].setAlignment(Qt.AlignRight)
        self.setWordWrap(True)
        self.setContentsMargins(3, 3, 3, 3)
