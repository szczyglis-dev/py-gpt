#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.29 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QLabel
import webbrowser


class HelpLabel(QLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setWordWrap(True)
        self.setContentsMargins(3, 3, 3, 3)
        self.setProperty('class', 'label-help')


class TitleLabel(QLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setProperty('class', 'label-title')


class ChatStatusLabel(QLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignRight)
        self.setProperty('class', 'label-chat-status')


class UrlLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self.text = text
        self.url = url
        self.update_url()
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip(url)

    def update_url(self):
        text = self.text
        if text is not None and len(text) > 0:
            text += ': '
        text += self.url
        self.setText(text)

    def mousePressEvent(self, event):
        webbrowser.open(self.url)
