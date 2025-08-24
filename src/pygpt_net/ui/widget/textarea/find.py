#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtWidgets import QLineEdit


class FindInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        Find input

        :param window: main window
        :param id: info window id
        """
        super().__init__(window)

        self.window = window
        self.id = id
        self.textChanged.connect(self._on_text_changed)

    @QtCore.Slot(str)
    def _on_text_changed(self, text):
        self.window.controller.finder.search_text_changed(text)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super().keyPressEvent(event)

        # update on Enter
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.window.controller.finder.focus_input(self.text())

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        super().focusInEvent(e)
        self.window.controller.finder.focus_input(self.text())