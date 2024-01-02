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

from PySide6.QtWidgets import QTextEdit


class OptionTextarea(QTextEdit):
    def __init__(self, window=None, id=None, autoupdate=False, section=None):
        """
        Settings input

        :param window: main window
        :param id: option id
        :param autoupdate: auto update
        :param section: settings section
        """
        super(OptionTextarea, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.autoupdate = autoupdate
        self.update_ui = True
        self.setAcceptRichText(False)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(OptionTextarea, self).keyPressEvent(event)
        if not self.autoupdate:
            return
        self.window.controller.settings.editor.change(self.id, self.toPlainText(), self.section)
        if self.update_ui:
            self.window.controller.ui.update()
