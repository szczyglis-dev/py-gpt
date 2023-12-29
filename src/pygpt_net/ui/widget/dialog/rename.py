#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QPushButton

from pygpt_net.utils import trans
from pygpt_net.ui.widget.textarea.rename import RenameInput


class RenameDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Rename dialog

        :param window: main window
        :param id: info window id
        """
        super(RenameDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.current = None
        self.input = RenameInput(window, id)
        self.input.setMinimumWidth(400)

        self.window.ui.nodes['dialog.rename.btn.update'] = QPushButton(trans('dialog.rename.update'))
        self.window.ui.nodes['dialog.rename.btn.update'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.accept_rename(self.id, self.window.ui.dialog['rename'].current,
                                                                 self.input.text()))

        self.window.ui.nodes['dialog.rename.btn.dismiss'] = QPushButton(trans('dialog.rename.dismiss'))
        self.window.ui.nodes['dialog.rename.btn.dismiss'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss_rename())

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.rename.btn.dismiss'])
        bottom.addWidget(self.window.ui.nodes['dialog.rename.btn.update'])

        self.window.ui.nodes['dialog.rename.label'] = QLabel(trans("dialog.rename.title"))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.rename.label'])
        layout.addWidget(self.input)
        layout.addLayout(bottom)

        self.setLayout(layout)
