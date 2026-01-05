#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt

from .base import BaseDialog


class RemoteStoreDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Remote stores dialog

        :param window: main window
        :param id: settings id
        """
        super(RemoteStoreDialog, self).__init__(window, id)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.controller.remote_store.dialog = False
        self.window.controller.remote_store.update()
        super(RemoteStoreDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()
        else:
            super(RemoteStoreDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.controller.remote_store.dialog = False
        self.window.controller.remote_store.update()