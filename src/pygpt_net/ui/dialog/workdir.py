#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy

from pygpt_net.ui.widget.dialog.workdir import WorkdirDialog
from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.option.input import DirectoryInput
from pygpt_net.utils import trans


class Workdir:
    def __init__(self, window=None):
        """
        Workdir change dialog

        :param window: Window instance
        """
        self.window = window
        self.path = None

    def setup(self):
        """Setup change directory dialog"""
        size_needed = self.window.core.filesystem.get_directory_size(self.window.core.config.get_user_path())
        self.window.ui.nodes['workdir.change.info'] = QLabel(trans("dialog.workdir.tip").format(size=size_needed))
        self.window.ui.nodes['workdir.change.info'].setWordWrap(True)
        self.window.ui.nodes['workdir.change.info'].setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.window.ui.nodes['workdir.change.info'].setMinimumWidth(300)

        self.window.ui.nodes['workdir.change.update.btn'] = QPushButton(trans("dialog.workdir.update.btn"))
        self.window.ui.nodes['workdir.change.update.btn'].clicked.connect(
            lambda: self.change_directory())

        self.window.ui.nodes['workdir.change.reset.btn'] = QPushButton(trans("dialog.workdir.reset.btn"))
        self.window.ui.nodes['workdir.change.reset.btn'].clicked.connect(
            lambda: self.reset_directory())

        self.window.ui.nodes['workdir.change.path'] = QLabel(self.window.core.config.get_user_path())
        self.window.ui.nodes['workdir.change.status'] = QLabel("")
        self.window.ui.nodes['workdir.change.status'].setVisible(False)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['workdir.change.reset.btn'])
        bottom_layout.addWidget(self.window.ui.nodes['workdir.change.update.btn'])

        # Create horizontal layout for the path and the button
        option = {
            'type': 'text',
            'label': 'Directory',
            'value': self.window.core.config.get_user_path(),
        }
        self.path = DirectoryInput(self.window, 'config', 'workdir', option)

        # Main layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['workdir.change.info'])
        layout.addWidget(self.path)
        layout.addLayout(bottom_layout)
        layout.addWidget(self.window.ui.nodes['workdir.change.status'], alignment=Qt.AlignCenter)

        self.window.ui.dialog['workdir.change'] = WorkdirDialog(self.window)
        self.window.ui.dialog['workdir.change'].setLayout(layout)
        self.window.ui.dialog['workdir.change'].setWindowTitle(trans("dialog.workdir.title"))

    def change_directory(self):
        """Update working directory"""
        self.window.controller.settings.migrate_workdir(self.path.text())

    def reset_directory(self):
        """Reset working directory"""
        current = self.window.core.config.get_user_path()
        self.path.value = current
        self.path.setText(current)

