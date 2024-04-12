#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.12 10:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QPushButton

from pygpt_net.utils import trans


class ConfirmDialog(QDialog):
    def __init__(self, window=None, type=None, id=None, parent_object=None):
        """
        Confirm dialog

        :param window: main window
        :param type: confirm type
        :param id: confirm id
        """
        super(ConfirmDialog, self).__init__(window)
        self.window = window
        self.type = type
        self.id = id
        self.parent_object = parent_object
        self.setWindowTitle(trans('dialog.confirm.title'))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # always on top

        self.window.ui.nodes['dialog.confirm.btn.yes'] = QPushButton(trans('dialog.confirm.yes'))
        self.window.ui.nodes['dialog.confirm.btn.yes'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.accept(self.type, self.id, self.parent_object))

        self.window.ui.nodes['dialog.confirm.btn.no'] = QPushButton(trans('dialog.confirm.no'))
        self.window.ui.nodes['dialog.confirm.btn.no'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss(self.type, self.id))

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.confirm.btn.no'])
        bottom.addWidget(self.window.ui.nodes['dialog.confirm.btn.yes'])

        self.layout = QVBoxLayout()
        self.message = QLabel("")
        self.message.setContentsMargins(10, 10, 10, 10)
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setMinimumWidth(400)
        self.message.setWordWrap(True)
        self.layout.addWidget(self.message)
        self.layout.addLayout(bottom)
        self.setLayout(self.layout)
