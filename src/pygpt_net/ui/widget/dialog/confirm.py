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

        btn_yes = QPushButton(trans('dialog.confirm.yes'))
        btn_yes.clicked.connect(
            lambda: self.window.controller.dialogs.confirm.accept(self.type, self.id, self.parent_object))

        btn_no = QPushButton(trans('dialog.confirm.no'))
        btn_no.clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss(self.type, self.id))

        bottom = QHBoxLayout()
        bottom.addWidget(btn_no)
        bottom.addWidget(btn_yes)

        self.layout = QVBoxLayout()
        self.message = QLabel("")
        self.message.setContentsMargins(10, 10, 10, 10)
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setMinimumWidth(400)
        self.layout.addWidget(self.message)
        self.layout.addLayout(bottom)
        self.setLayout(self.layout)
