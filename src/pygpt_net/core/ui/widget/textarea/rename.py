#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 18:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtWidgets import QLineEdit


class RenameInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        Rename dialog

        :param window: main window
        :param id: info window id
        """
        super(RenameInput, self).__init__(window)

        self.window = window
        self.id = id
        self.setStyleSheet(self.window.controller.theme.get_style('line_edit'))

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(RenameInput, self).keyPressEvent(event)

        # save on Enter
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.window.controller.confirm.accept_rename(self.window.ui.dialog['rename'].id,
                                                         self.window.ui.dialog['rename'].current,
                                                         self.text())
