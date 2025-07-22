#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of the PYGPT package           #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.22 15:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLineEdit, QStyle
from PySide6.QtCore import QTimer

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class CtxSearchInput(QLineEdit):
    def __init__(self, window=None):
        """
        Search input

        :param window: Window instance
        """
        super(CtxSearchInput, self).__init__(window)
        self.window = window
        self.setPlaceholderText(trans('ctx.list.search.placeholder'))
        self.setProperty('class', 'layout-search')

        # action for clearing the search
        self.clear_action = QAction(self)
        self.clear_action.setIcon(QIcon(":/icons/close.svg"))
        self.clear_action.triggered.connect(self.clear_search_string)
        self.addAction(self.clear_action, QLineEdit.TrailingPosition)
        self.clear_action.setVisible(False)

        # search action - icon on the left
        action = QAction(self)
        action.setIcon(QIcon(":/icons/search.svg"))
        self.addAction(action, QLineEdit.LeadingPosition)

        # timer to delay search_string_change
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)  # delay of 300 ms
        self._search_timer.timeout.connect(self._execute_search)

        # start the timer each time the text changes
        self.textChanged.connect(self.on_text_changed)

    def clear_search_string(self):
        """Clear input"""
        self.clear()
        self._search_timer.stop()  # stop the timer to prevent triggering the search action
        self.window.controller.ctx.search_string_clear()

    def on_text_changed(self, text):
        """
        On text changed

        :param text: text entered by the user
        """
        self.clear_action.setVisible(bool(text))
        # restart the timer each time the text changes - ensures the action is only triggered
        # after a pause in typing
        self._search_timer.start()

    def _execute_search(self):
        """Invoke the search action after a specified delay."""
        search_text = self.text()
        self.window.controller.ctx.search_string_change(search_text)

    def focusInEvent(self, event):
        """
        Focus in event

        :param event: focus event
        """
        super(CtxSearchInput, self).focusInEvent(event)
        self.window.controller.ctx.search_focus_in()