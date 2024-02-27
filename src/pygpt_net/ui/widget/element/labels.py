#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 18:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QTimer, QRect, Signal
from PySide6.QtGui import QCursor, QAction, QIcon
from PySide6.QtWidgets import QLabel, QLineEdit, QToolTip
import webbrowser

from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        # self.setWordWrap(True)

    def update_url(self):
        text = self.text
        if text is not None and len(text) > 0:
            text += ': '
        text += self.url
        self.setText(text)

    def mousePressEvent(self, event):
        webbrowser.open(self.url)


class CmdLabel(QLineEdit):
    def __init__(self, window=None, text: str = ""):
        """
        Command label

        :param window: main window
        :param text: text
        """
        super(CmdLabel, self).__init__(window)
        self.window = window
        self.setStyleSheet(
            "font-weight: bold;"
            "font-size: 14px;"
            "padding: 5px;"
            "background: #020202;"
            "color: #fff;"
            "text-align: center;"
        )
        self.setText(text)
        self.setAlignment(Qt.AlignCenter)
        self.setReadOnly(True)
        self.action = QAction(self)
        self.action.setIcon(QIcon(":/icons/copy.svg"))
        self.action.triggered.connect(self.copy_to_clipboard)
        self.addAction(self.action, QLineEdit.TrailingPosition)

    def copy_to_clipboard(self):
        """Copy to clipboard"""
        self.selectAll()
        self.copy()
        self.deselect()
        self.action.setIcon(QIcon(":/icons/check.svg"))
        QToolTip.showText(QCursor.pos(), trans("clipboard.copied"), self, QRect(), 2000)
        timer = QTimer()
        timer.singleShot(2000, self.reset_icon)

    def reset_icon(self):
        """Reset icon"""
        self.action.setIcon(QIcon(":/icons/copy.svg"))


class IconLabel(QLabel):
    clicked = Signal()

    def __init__(self, icon: str, window=None):
        super().__init__("", window)
        self.window = window
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignRight)
        self.setProperty('class', 'label-chat-status')
        self.setContentsMargins(0, 0, 0, 0)
        self.set_icon(icon)

    def set_icon(self, icon: str):
        self.setPixmap(QIcon(icon).pixmap(16, 16))

    def mousePressEvent(self, event):
        self.clicked.emit()
