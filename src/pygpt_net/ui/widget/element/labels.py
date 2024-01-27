#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 11:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
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
        self.url = url
        if text is not None and len(text) > 0:
            text += ': '
        self.setText(
            f"<a href='{self.url}' style='text-decoration:none; color:#90d9ff; font-weight:bold;'>{text}{self.url}</a>")
        self.setTextFormat(Qt.RichText)
        self.setOpenExternalLinks(False)
        self.linkActivated.connect(self.open_url)
        self.setProperty('class', 'label-link')  # won't work

    def open_url(self, url):
        """
        Open url in default browser

        :param url: Url to open
        """
        webbrowser.open(url)

    def enterEvent(self, event):
        self.setStyleSheet('''
        color: #FFFFFF;
        text-decoration: underline;
        ''')
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet('''
        QLabel {
            color: #90d9ff;
            text-decoration: none;
        }
        ''')
        super().leaveEvent(event)
