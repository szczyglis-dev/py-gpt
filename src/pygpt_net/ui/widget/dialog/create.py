#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 19:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QPushButton

from pygpt_net.utils import trans
from pygpt_net.ui.widget.textarea.create import CreateInput


class CreateDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Create dialog

        :param window: main window
        :param id: info window id
        """
        super(CreateDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.current = None
        self.input = CreateInput(window, id)
        self.input.setMinimumWidth(400)

        self.window.ui.nodes['dialog.create.btn.update'] = QPushButton(trans('dialog.create.update'))
        self.window.ui.nodes['dialog.create.btn.update'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.accept_create(
                self.id,
                self.window.ui.dialog['create'].current,
                self.input.text()),
        )

        self.window.ui.nodes['dialog.create.btn.dismiss'] = QPushButton(trans('dialog.create.dismiss'))
        self.window.ui.nodes['dialog.create.btn.dismiss'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss_create())

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.create.btn.dismiss'])
        bottom.addWidget(self.window.ui.nodes['dialog.create.btn.update'])

        self.window.ui.nodes['dialog.create.label'] = QLabel(trans("dialog.create.title"))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.create.label'])
        layout.addWidget(self.input)
        layout.addLayout(bottom)

        self.setLayout(layout)
