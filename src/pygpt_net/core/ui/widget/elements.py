#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 16:00:00                  #
# ================================================== #
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QWidget, QVBoxLayout, QLabel


class CollapsedGroup(QWidget):
    def __init__(self, window=None, id=None, title=None, value=False, section=None):
        """
        Collapsed settings group

        :param window: Window instance
        :param id: option id
        :param title: option title
        :param value: current value
        :param section: settings section
        """
        super(CollapsedGroup, self).__init__(window)
        self.window = window
        self.id = id
        self.title = title
        self.value = value
        self.section = section

        # checkbox show/hide
        self.box = QCheckBox('Show/hide', self.window)
        self.box.setMinimumHeight(30)
        self.box.setStyleSheet("font-weight: bold;")
        self.box.setChecked(value)
        self.box.stateChanged.connect(
            lambda: self.window.controller.settings.toggle_collapsed(self.id, self.box.isChecked(), self.section))

        # options layout
        self.options = QVBoxLayout()
        self.options.setContentsMargins(0, 0, 0, 0)

        options_widget = QWidget(self)
        options_widget.setLayout(self.options)
        options_widget.setVisible(self.value)
        options_widget.setContentsMargins(0, 0, 0, 0)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.box)
        self.layout.addWidget(options_widget)

        self.setLayout(self.layout)

    def collapse(self, value):
        """
        Expand or collapse group

        :param value: collapsed state (True/False)
        """
        self.box.setChecked(value)
        self.options.parentWidget().setVisible(value)

    def add_layout(self, option):
        """
        Add option to group

        :param option: option widget
        """
        self.options.addLayout(option)

    def add_widget(self, option):
        """
        Add option to group

        :param option: option widget
        """
        self.options.addWidget(option)


class UrlLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self.url = url
        self.setText(f"<a href='{self.url}' style='text-decoration:none; color:#90d9ff; font-weight:bold;'>{text}: {self.url}</a>")
        self.setTextFormat(Qt.RichText)
        self.setOpenExternalLinks(False)
        self.linkActivated.connect(self.open_url)
        self.setStyleSheet('''
        QLabel {
            color: #90d9ff;
            text-decoration: none;
        }
        ''')

    def open_url(self, url):
        webbrowser.open(url)

    def enterEvent(self, event):
        self.setStyleSheet('''
        QLabel {
            color: #FFFFFF;
            text-decoration: underline;
        }
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
