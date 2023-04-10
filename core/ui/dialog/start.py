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

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton

from core.ui.widgets import InfoDialog
from core.utils import trans


class Start:
    def __init__(self, window=None):
        self.window = window

    def setup(self):
        """Setup start dialog"""
        id = 'start'

        btn = QPushButton(trans('dialog.start.btn'))
        btn.clicked.connect(lambda: self.window.controller.settings.start_settings())

        logo_label = QLabel()
        pixmap = QPixmap('./data/logo.png')
        logo_label.setPixmap(pixmap)

        string = trans('dialog.start.text')
        label = QLabel(string)
        label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(btn)

        self.window.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.dialog['info.' + id].setLayout(layout)
        self.window.dialog['info.' + id].setWindowTitle(trans("dialog.start.title"))
