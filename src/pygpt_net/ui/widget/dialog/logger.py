#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog


class LoggerDialog(QDialog):
    def __init__(self, window=None):
        """
        Logger dialog

        :param window: main window
        """
        super(LoggerDialog, self).__init__(window)
        self.window = window

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        event.accept()

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(LoggerDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.controller.debug.is_logger = False
        self.window.controller.debug.logger_close()
        self.window.controller.debug.update()
