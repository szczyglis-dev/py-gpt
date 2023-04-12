#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.12 08:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton

from core.ui.widgets import InfoDialog
from core.utils import trans


class Start:
    def __init__(self, window=None):
        """
        Start dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups start dialog"""
        id = 'start'

        self.window.data['start.btn'] = QPushButton(trans('dialog.start.btn'))
        self.window.data['start.btn'].clicked.connect(lambda: self.window.controller.settings.start_settings())

        logo_label = QLabel()
        pixmap = QPixmap('./data/logo.png')
        logo_label.setPixmap(pixmap)

        self.window.data['start.title'] = QLabel(trans('dialog.start.title.text'))
        link = QLabel(trans('dialog.start.link'))
        self.window.data['start.settings'] = QLabel(trans('dialog.start.settings.text'))
        self.window.data['start.settings'].setAlignment(Qt.AlignCenter)

        self.window.data['start.title'].setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.window.data['start.title'], alignment=Qt.AlignCenter)
        layout.addWidget(link, alignment=Qt.AlignCenter)
        layout.addWidget(self.window.data['start.settings'], alignment=Qt.AlignCenter)
        layout.addWidget(self.window.data['start.btn'])

        self.window.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.dialog['info.' + id].setLayout(layout)
        self.window.dialog['info.' + id].setWindowTitle(trans("dialog.start.title"))
