#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

import os

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QLabel

from core.ui.widgets import InfoDialog
from core.utils import trans


class Changelog:
    def __init__(self, window=None):
        """
        Changelog dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups change log dialog"""
        id = 'changelog'

        txt = ''
        try:
            with open(os.path.join(".", "CHANGELOG.txt"), "r") as f:
                txt = f.read()
                f.close()
        except Exception as e:
            print(e)

        textarea = QPlainTextEdit()
        textarea.setReadOnly(True)
        textarea.setPlainText(txt)

        self.window.data['dialog.changelog.label'] = QLabel(trans("dialog.changelog.title"))
        layout = QVBoxLayout()
        layout.addWidget(self.window.data['dialog.changelog.label'])
        layout.addWidget(textarea)

        self.window.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.dialog['info.' + id].setLayout(layout)
        self.window.dialog['info.' + id].setWindowTitle(trans("dialog.changelog.title"))
