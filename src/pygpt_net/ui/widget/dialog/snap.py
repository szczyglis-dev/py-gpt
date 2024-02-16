#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.16 16:00:00                  #
# ================================================== #

import os
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton, QPlainTextEdit, QHBoxLayout, QCheckBox, \
    QDialogButtonBox

from pygpt_net.ui.widget.element.labels import TitleLabel, CmdLabel
from pygpt_net.utils import trans


class SnapDialog(QDialog):
    def __init__(self, window=None):
        """
        Snap dialog

        :param window: main window
        """
        super(SnapDialog, self).__init__(window)
        self.window = window
        self.setParent(window)
        self.setWindowTitle("Snap detected")
        self.cmd = CmdLabel(self.window, "sudo snap connect pygpt:camera")

        self.btn = QPushButton("OK")
        self.btn.clicked.connect(self.accept)
        self.btn.setStyleSheet("margin: 10px 0px 0px 0px;")

        # layout
        self.layout = QVBoxLayout()
        self.message = QLabel(
            "Camera is not opened! It must be connected in Snap environment.\n"
            "Run the following command to enable the camera:")
        self.message.setStyleSheet("margin: 10px 0px 10px 0px;")
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.cmd)
        self.layout.addWidget(self.btn)
        self.layout.addStretch()
        self.setLayout(self.layout)
