#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.01 18:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QLabel, QPushButton

from pygpt_net.ui.widget.dialog.license import LicenseDialog
from pygpt_net.utils import trans


class License:
    def __init__(self, window=None):
        """
        Liciense dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup license dialog"""
        id = 'license'

        txt = ''
        try:
            with open(os.path.join(
                    self.window.core.config.get_app_path(),
                    "LICENSE"), "r", encoding="utf-8"
            ) as f:
                txt = f.read()
        except Exception as e:
            print(e)

        textarea = QPlainTextEdit()
        textarea.setReadOnly(True)
        textarea.setPlainText(txt)

        self.window.ui.nodes['dialog.license.accept'] = QPushButton(trans("dialog.license.accept"))
        self.window.ui.nodes['dialog.license.accept'].clicked.connect(self.accept)

        self.window.ui.nodes['dialog.license.label'] = QLabel(trans("dialog.license.label"))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.license.label'])
        layout.addWidget(textarea)
        layout.addWidget(self.window.ui.nodes['dialog.license.accept'])

        self.window.ui.dialog['info.' + id] = LicenseDialog(self.window, id)
        self.window.ui.dialog['info.' + id].setLayout(layout)
        self.window.ui.dialog['info.' + id].setWindowTitle(trans("dialog.license.title"))

    def accept(self):
        """Accept license"""
        self.window.core.config.set('license.accepted', True)
        self.window.core.config.save()
        self.window.ui.dialog['info.license'].close()
