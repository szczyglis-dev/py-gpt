#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.10 23:00:00                  #
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
        super(FindInput, self).__init__(window)

        self.window = window
        self.id = id
        self.textChanged.connect(
            lambda: self.window.controller.finder.search_text_changed(self.text()),
        )

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(FindInput, self).keyPressEvent(event)

        # update on Enter
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.window.controller.finder.focus_input(self.text())

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        super(FindInput, self).focusInEvent(e)
        self.window.controller.finder.focus_input(self.text())

