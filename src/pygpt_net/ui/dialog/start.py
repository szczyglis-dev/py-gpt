#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 16:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton

from pygpt_net.ui.widget.dialog.info import InfoDialog
from pygpt_net.ui.widget.element.labels import UrlLabel
from pygpt_net.utils import trans


class Start:
    def __init__(self, window=None):
        """
        Start dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup start dialog"""
        id = 'start'

        self.window.ui.nodes['start.btn'] = QPushButton(trans('dialog.start.btn'))
        self.window.ui.nodes['start.btn'].clicked.connect(lambda: self.window.controller.settings.welcome_settings())

        logo_label = QLabel()
        path = os.path.abspath(
            os.path.join(self.window.core.config.get_app_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        self.window.ui.nodes['start.title'] = QLabel(trans('dialog.start.title.text'))
        link = UrlLabel('', trans('dialog.start.link'))
        self.window.ui.nodes['start.settings'] = QLabel(trans('dialog.start.settings.text'))
        self.window.ui.nodes['start.settings'].setAlignment(Qt.AlignCenter)

        self.window.ui.nodes['start.title'].setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.window.ui.nodes['start.title'], alignment=Qt.AlignCenter)
        layout.addWidget(link, alignment=Qt.AlignCenter)
        layout.addWidget(self.window.ui.nodes['start.settings'], alignment=Qt.AlignCenter)
        layout.addWidget(self.window.ui.nodes['start.btn'])

        self.window.ui.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.ui.dialog['info.' + id].setLayout(layout)
        self.window.ui.dialog['info.' + id].setWindowTitle(trans("dialog.start.title"))
