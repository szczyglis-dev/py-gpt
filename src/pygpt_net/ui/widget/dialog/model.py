#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.17 20:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from .base import BaseDialog


class ModelDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Models dialog

        :param window: main window
        :param id: settings id
        """
        super(ModelDialog, self).__init__(window, id)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.controller.model.editor.dialog = False
        self.window.controller.model.update()
        super(ModelDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(ModelDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.controller.model.editor.dialog = False
        self.window.controller.model.update()
