#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.16 18:35:00                  #
# ================================================== #

from PySide6.QtCore import Qt

from .base import BaseDialog


class AgentsV2EditorDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        super().__init__(window, id)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        self.window.controller.agents_v2.editor.dialog = False
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
