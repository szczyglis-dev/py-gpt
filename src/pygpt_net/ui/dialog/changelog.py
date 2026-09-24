#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 12:31:00
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QLabel

from pygpt_net.ui.widget.dialog.info import InfoDialog
from pygpt_net.utils import trans


class Changelog:
    def __init__(self, window=None):
        """
        Changelog dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup change log dialog"""
        id = 'changelog'

        txt = ''
        try:
            with open(os.path.join(
                    self.window.core.config.get_app_path(),
                    "CHANGELOG.txt"), "r", encoding="utf-8") as f:
                txt = f.read()
        except Exception as e:
            print(e)

        textarea = QPlainTextEdit()
        textarea.setReadOnly(True)
        textarea.setPlainText(txt)

        self.window.ui.nodes['dialog.changelog.label'] = QLabel(trans("dialog.changelog.title"))

        updated = QLabel(
            trans("dialog.changelog.updated").format(version=self.window.meta["version"])
        )
        updated.setAlignment(Qt.AlignCenter)
        updated.setWordWrap(True)
        updated.setContentsMargins(12, 10, 12, 10)
        font = updated.font()
        font.setBold(True)
        updated.setFont(font)
        updated.setVisible(bool(self.window.core.config.get("app_updated", False)))
        self.window.ui.nodes['dialog.changelog.updated'] = updated

        layout = QVBoxLayout()
        layout.addWidget(updated)
        layout.addWidget(self.window.ui.nodes['dialog.changelog.label'])
        layout.addWidget(textarea)

        self.window.ui.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.ui.dialog['info.' + id].setLayout(layout)
        self.window.ui.dialog['info.' + id].setWindowTitle(trans("dialog.changelog.title"))
