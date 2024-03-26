#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt

from .base import BaseDialog


class VideoPlayerDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        VideoPlayerDialog dialog

        :param window: main window
        :param id: info window id
        """
        super(VideoPlayerDialog, self).__init__(window, id)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(VideoPlayerDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(VideoPlayerDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.tools.get("player").on_close()
