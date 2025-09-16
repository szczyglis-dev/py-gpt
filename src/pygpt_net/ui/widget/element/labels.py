#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.16 22:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QTimer, QRect, Signal, QUrl, QEvent
from PySide6.QtGui import QCursor, QAction, QIcon, QDesktopServices, QPainter, QPixmap, QColor
from PySide6.QtWidgets import QLabel, QLineEdit, QToolTip

from pygpt_net.utils import trans


class BaseLabel(QLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setWordWrap(True)
        self.setContentsMargins(3, 3, 3, 3)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

class HelpLabel(BaseLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setProperty('class', 'label-help')

class DescLabel(BaseLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setProperty('class', 'label-desc')


class TitleLabel(QLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setProperty('class', 'label-title')
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)


class ChatStatusLabel(QLabel):
    def __init__(self, text, window=None):
        super().__init__(text, window)
        self.window = window
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignRight)
        self.setProperty('class', 'label-chat-status')
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)


class UrlLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self.text = text
        self.url = url
        self.update_url()
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip(url)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # self.setWordWrap(True)

    def update_url(self):
        text = self.text
        if text is not None and len(text) > 0:
            text += ': '
        text += self.url
        self.setText(text)

    def mousePressEvent(self, event):
        if self.window and hasattr(self.window, 'controller'):
            self.window.controller.dialogs.info.open_url(self.url)
        else:
            QDesktopServices.openUrl(QUrl(self.url))


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
        self.setMouseTracking(True)

        self.original_pixmap = None
        self.hover_pixmap = None
        self.set_icon(icon)

    def sizeHint(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            return self.original_pixmap.size()
        return super().sizeHint()

    def minimumSizeHint(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            return self.original_pixmap.size()
        return super().minimumSizeHint()

    def set_icon(self, icon: str):
        icon_obj = QIcon(icon)
        self.original_pixmap = icon_obj.pixmap(16, 16)
        if self.original_pixmap.isNull():
            return
        self.setPixmap(self.original_pixmap)

    def create_hover_icon(self, pixmap: QPixmap) -> QPixmap:
        if pixmap.isNull():
            return pixmap

        recolored = QPixmap(pixmap.size())
        recolored.setDevicePixelRatio(pixmap.devicePixelRatio())
        recolored.fill(Qt.transparent)

        painter = QPainter(recolored)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)

        is_dark = False
        if self.window and self.window.core and self.window.core.config:
            theme = self.window.core.config.get("theme", "default")
            if theme.startswith("dark"):
                is_dark = True

        if is_dark:
            painter.fillRect(recolored.rect(), QColor("#c4c4c4"))
        else:
            painter.fillRect(recolored.rect(), QColor("#000000"))
        painter.end()

        return recolored

    def enterEvent(self, event: QEvent):
        self.setCursor(Qt.PointingHandCursor)
        self.hover_pixmap = self.create_hover_icon(self.original_pixmap)
        if self.hover_pixmap is not None and not self.hover_pixmap.isNull():
            self.setPixmap(self.hover_pixmap)
        else:
            self.setPixmap(self.original_pixmap)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self.unsetCursor()
        self.setPixmap(self.original_pixmap)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)