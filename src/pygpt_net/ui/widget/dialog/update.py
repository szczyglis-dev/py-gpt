#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 11:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton, QPlainTextEdit, QHBoxLayout, QCheckBox

from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.utils import trans


class UpdateDialog(QDialog):
    def __init__(self, window=None):
        """
        Update dialog

        :param window: main window
        """
        super(UpdateDialog, self).__init__(window)
        self.window = window
        self.setParent(window)
        self.setWindowTitle(trans('update.title'))

        self.download = QPushButton(trans('update.download'))
        self.download.setCursor(Qt.PointingHandCursor)
        self.download.clicked.connect(
            lambda: self.window.controller.dialogs.info.goto_update())

        self.snap = QPushButton(trans('update.snap'))
        self.snap.setCursor(Qt.PointingHandCursor)
        self.snap.clicked.connect(
            lambda: self.window.controller.dialogs.info.goto_snap())

        self.changelog = QPlainTextEdit()
        self.changelog.setReadOnly(True)
        self.changelog.setMinimumHeight(200)

        logo_label = QLabel()
        path = os.path.abspath(
            os.path.join(self.window.core.config.get_app_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        buttons = QHBoxLayout()
        buttons.addWidget(self.download)
        buttons.addWidget(self.snap)

        self.checkbox_startup = QCheckBox(trans("updater.check.launch"))
        self.checkbox_startup.stateChanged.connect(
            lambda: self.window.controller.launcher.toggle_update_check(
                self.checkbox_startup.isChecked()))

        if self.window.core.config.get('updater.check.launch'):
            self.checkbox_startup.setChecked(True)
        else:
            self.checkbox_startup.setChecked(False)

        self.layout = QVBoxLayout()
        self.message = QLabel("")
        self.info = TitleLabel(trans("update.info"))
        self.info.setWordWrap(True)
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setStyleSheet("font-weight: bold; font-size: 12px; margin: 20px 0px 20px 0px;")
        self.info.setMaximumHeight(60)
        self.layout.addWidget(logo_label)
        self.layout.addWidget(self.info)
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.changelog, 1)
        self.layout.addWidget(self.checkbox_startup)
        self.layout.addLayout(buttons)
        self.layout.addStretch()
        self.setLayout(self.layout)
