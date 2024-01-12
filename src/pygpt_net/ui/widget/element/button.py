#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 21:00:00                  #
# ================================================== #


from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


class ContextMenuButton(QPushButton):
    def __init__(self, title, parent=None, action=None):
        super().__init__(title, parent)
        self.action = action

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            self.action(self, event.pos())
        else:
            super().mousePressEvent(event)
