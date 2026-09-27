#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 20:15:00                  #
# ================================================== #

from PySide6.QtCore import Qt

from .base import BaseDialog


class QuickStartDialog(BaseDialog):
    """First-run quick-start wizard dialog."""

    def __init__(self, window=None, id=None):
        super(QuickStartDialog, self).__init__(window, id)
        self.window = window
        self.id = id
        self.completed = False
        self.disable_geometry_store = True
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)

    def closeEvent(self, event):
        """Keep the first-run wizard open until Finish is used."""
        if not self.completed:
            event.ignore()
            return
        super(QuickStartDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """Do not dismiss the mandatory first-run wizard with Escape."""
        if event.key() == Qt.Key_Escape and not self.completed:
            event.ignore()
            return
        super(QuickStartDialog, self).keyPressEvent(event)
