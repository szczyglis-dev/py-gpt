#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 02:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtWidgets import QLineEdit


class UrlInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        Url dialog input

        :param window: main window
        :param id: info window id
        """
        super(UrlInput, self).__init__(window)

        self.window = window
        self.id = id

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(UrlInput, self).keyPressEvent(event)

        # save on Enter
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.window.controller.dialogs.confirm.accept_url(
                self.window.ui.dialog['url'].id,
                self.window.ui.dialog['url'].current,
                self.text(),
            )
