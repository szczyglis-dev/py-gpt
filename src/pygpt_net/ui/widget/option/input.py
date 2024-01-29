#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.29 18:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLineEdit
import pygpt_net.icons_rc


class OptionInputInline(QLineEdit):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings inline input

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionInputInline, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = False
        self.title = ""
        self.real_time = False
        self.slider = False  # True if connected slider
        self.setMaximumWidth(60)
        self.returnPressed.connect(self.on_return_pressed)

        # from option data
        if self.option is not None:
            if "label" in self.option:
                self.title = self.option["label"]
            if "value" in self.option:
                self.value = self.option["value"]
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

    def focusOutEvent(self, event):
        """On focus out event"""
        super(OptionInputInline, self).focusOutEvent(event)
        self.handle_value_change()

    def on_return_pressed(self):
        """On return key pressed event"""
        self.handle_value_change()

    def handle_value_change(self):
        """Value changed event"""
        if self.slider:
            self.window.controller.config.slider.on_update(self.parent_id, self.id, self.option, self.text(), "input")
        if not self.real_time:
            return
        self.window.controller.config.input.on_update(self.parent_id, self.id, self.option, self.text())


class OptionInput(QLineEdit):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings input

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionInput, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = False
        self.title = ""
        self.real_time = False

        # from option data
        if self.option is not None:
            if "label" in self.option:
                self.title = self.option["label"]
            if "value" in self.option:
                self.value = self.option["value"]
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(OptionInput, self).keyPressEvent(event)
        if not self.real_time:
            return
        self.window.controller.ui.update()
        self.window.controller.config.input.on_update(self.parent_id, self.id, self.option, self.text())


class PasswordInput(QLineEdit):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings password input

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(PasswordInput, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = False
        self.title = ""
        self.real_time = False

        # from option data
        if self.option is not None:
            if "label" in self.option:
                self.title = self.option["label"]
            if "value" in self.option:
                self.value = self.option["value"]
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

        self.setEchoMode(QLineEdit.Password)
        self.toggle_password_action = QAction('+', self)
        self.toggle_password_action.triggered.connect(self.toggle_password_visibility)
        action = QAction(self)
        action.setIcon(QIcon(":/icons/view.svg"))
        action.triggered.connect(self.toggle_password_visibility)
        self.addAction(action, QLineEdit.TrailingPosition)
        self.is_password_shown = False

    def toggle_password_visibility(self):
        if self.is_password_shown:
            self.setEchoMode(QLineEdit.Password)
            self.toggle_password_action.setText('+')
            self.is_password_shown = False
        else:
            self.setEchoMode(QLineEdit.Normal)
            self.toggle_password_action.setText('-')
            self.is_password_shown = True

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(PasswordInput, self).keyPressEvent(event)
        if not self.real_time:
            return
        self.window.controller.ui.update()
        self.window.controller.config.input.on_update(self.parent_id, self.id, self.option, self.text())
