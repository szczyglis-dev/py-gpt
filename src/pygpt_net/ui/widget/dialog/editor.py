#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.09 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from .base import BaseDialog


class EditorDialog(BaseDialog):
    def __init__(self, window=None, id=None, data_id=None):
        """
        EditorDialog

        :param window: main window
        :param id: configurator id
        :param data_id: data id
        """
        super(EditorDialog, self).__init__(window, id)
        self.window = window
        self.id = id  # configurator id
        self.data_id = data_id  # current data id
        self.data = None  # data values
        self.options = None  # options dict
        self.idx = None  # current editing idx

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(EditorDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(EditorDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.core.settings.active[self.id] = False
