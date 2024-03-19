#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 01:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import Qt
from .base import BaseDialog


class EditorFileDialog(BaseDialog):
    def __init__(self, window=None, id="editor_file"):
        """
        File editor dialog

        :param window: main window
        :param id: dialog id
        """
        super(EditorFileDialog, self).__init__(window, id)
        self.window = window
        self.file = None
        self.base_content = None
        self.disable_geometry_store = False
        self.id = id

    def update_file_title(self, force: bool = False):
        """
        Update file title

        :param force: force update
        """
        if self.file:
            current = self.window.ui.editor[self.id].toPlainText()
            base = self.base_content
            title = os.path.basename(self.file)
            if current != base:
                title += "*"
            if current != base or force:
                time = datetime.datetime.now().strftime("%H:%M")
                title += " (" + time + ")"
            self.setWindowTitle(title)
        else:
            self.setWindowTitle("Untitled")

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(EditorFileDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(EditorFileDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        if self.id == "editor_file":
            self.window.core.settings.active['editor'] = False
            self.window.controller.settings.close('editor')
            self.window.controller.settings.update()
