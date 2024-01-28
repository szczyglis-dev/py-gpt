#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 19:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtWidgets import QLineEdit


class CreateInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        Create dialog input

        :param window: main window
        :param id: info window id
        """
        super(CreateInput, self).__init__(window)

        self.window = window
        self.id = id

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(CreateInput, self).keyPressEvent(event)

        # save on Enter
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.window.controller.dialogs.confirm.accept_create(
                self.window.ui.dialog['create'].id,
                self.window.ui.dialog['create'].current,
                self.text(),
            )
