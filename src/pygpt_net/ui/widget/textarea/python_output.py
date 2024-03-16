#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.13 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextBrowser, QMenu
from PySide6.QtGui import QDesktopServices, QAction, QIcon, QTextOption

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class PythonOutput(QTextBrowser):
    def __init__(self, window=None):
        """
        Python output

        :param window: main window
        """
        super(PythonOutput, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.value = self.window.core.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            self.window.core.config.data['font_size'] = self.value
            self.window.core.config.save()
            option = self.window.controller.settings.editor.get_option('font_size')
            option['value'] = self.value
            self.window.controller.config.apply(
                parent_id='config',
                key='font_size',
                option=option,
            )
            self.window.controller.ui.update_font_size()
            event.accept()
        else:
            super(PythonOutput, self).wheelEvent(event)
