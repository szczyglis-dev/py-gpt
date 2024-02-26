#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.26 22:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton

from pygpt_net.ui.widget.element.labels import CmdLabel


class SnapDialogCamera(QDialog):
    def __init__(self, window=None):
        """
        Snap dialog for camera

        :param window: main window
        """
        super(SnapDialogCamera, self).__init__(window)
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
            "Camera is not connected! It must be connected in Snap environment.\n"
            "Run the following command to enable the camera:")
        self.message.setStyleSheet("margin: 10px 0px 10px 0px;")
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.cmd)
        self.layout.addWidget(self.btn)
        self.layout.addStretch()
        self.setLayout(self.layout)


class SnapDialogAudioInput(QDialog):
    def __init__(self, window=None):
        """
        Snap dialog for audio input

        :param window: main window
        """
        super(SnapDialogAudioInput, self).__init__(window)
        self.window = window
        self.setParent(window)
        self.setWindowTitle("Snap is detected")
        self.cmd = CmdLabel(self.window, "sudo snap connect pygpt:audio-record :audio-record")

        self.btn = QPushButton("OK")
        self.btn.clicked.connect(self.accept)
        self.btn.setStyleSheet("margin: 10px 0px 0px 0px;")

        # layout
        self.layout = QVBoxLayout()
        self.message = QLabel(
            "Microphone is not connected! It must be connected in Snap environment.\n"
            "Run the following command to enable the microphone:")
        self.message.setStyleSheet("margin: 10px 0px 10px 0px;")
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.cmd)
        self.layout.addWidget(self.btn)
        self.layout.addStretch()
        self.setLayout(self.layout)
