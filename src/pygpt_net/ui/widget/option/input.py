#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QLineEdit


class OptionInputInline(QLineEdit):
    def __init__(self, window=None, id=None, section=None):
        """
        Settings input inline

        :param window: main window
        :param id: option id
        :param section: settings section
        """
        super(OptionInputInline, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.setMaximumWidth(60)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(OptionInputInline, self).keyPressEvent(event)
        self.window.controller.settings.apply(self.id, self.text(), 'input', self.section)


class OptionInput(QLineEdit):
    def __init__(self, window=None, id=None, autoupdate=False, section=None):
        """
        Settings input

        :param window: main window
        :param id: option id
        :param autoupdate: auto update
        :param section: settings section
        """
        super(OptionInput, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.autoupdate = autoupdate

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(OptionInput, self).keyPressEvent(event)
        if not self.autoupdate:
            return
        self.window.controller.ui.update()
        self.window.controller.settings.change(self.id, self.text(), self.section)
