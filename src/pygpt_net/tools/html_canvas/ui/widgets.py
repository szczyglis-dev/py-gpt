#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.11 23:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.textarea.editor import BaseCodeEditor
from pygpt_net.ui.widget.textarea.html import HtmlOutput

import pygpt_net.icons_rc

class CanvasOutput(HtmlOutput):
    def __init__(self, window=None):
        """
        HTML canvas output

        :param window: main window
        """
        super(CanvasOutput, self).__init__(window)
        self.window = window

class CanvasEdit(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Python interpreter output

        :param window: main window
        """
        super(CanvasEdit, self).__init__(window)
        self.window = window
        self.setReadOnly(False)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'interpreter-output')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)