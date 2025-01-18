#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.16 17:00:00                  #
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
        self.setWindowTitle("Snap version detected")
        self.cmd = CmdLabel(self.window, "sudo snap connect pygpt:camera")

        self.btn = QPushButton("OK")
        self.btn.clicked.connect(self.accept)
        self.btn.setStyleSheet("margin: 10px 0px 0px 0px;")

        # layout
        self.layout = QVBoxLayout()
        self.message = QLabel(
            "Camera not connected? It must be connected in the Snap environment.\n"
            "Run the following command to enable the camera and restart the application:")
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
        self.setWindowTitle("Snap version is detected")
        self.cmd = CmdLabel(self.window, "sudo snap connect pygpt:alsa && sudo snap connect pygpt:audio-record :audio-record")

        self.btn = QPushButton("OK")
        self.btn.clicked.connect(self.accept)
        self.btn.setStyleSheet("margin: 10px 0px 0px 0px;")

        # layout
        self.layout = QVBoxLayout()
        self.message = QLabel(
            "Tip: Microphone must be manually connected in the Snap environment.\n"
            "If it is connected, click on the OK button, and this warning will not be displayed again.\n"
            "If it is NOT connected yet, run the following command and restart the application:")
        self.message.setStyleSheet("margin: 10px 0px 10px 0px;")
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.cmd)
        self.layout.addWidget(self.btn)
        self.layout.addStretch()
        self.setLayout(self.layout)


class SnapDialogAudioOutput(QDialog):
    def __init__(self, window=None):
        """
        Snap dialog for audio output

        :param window: main window
        """
        super(SnapDialogAudioOutput, self).__init__(window)
        self.window = window
        self.setParent(window)
        self.setWindowTitle("Snap version is detected")
        self.cmd = CmdLabel(self.window, "sudo snap connect pygpt:alsa && sudo snap connect pygpt:audio-playback")

        self.btn = QPushButton("OK")
        self.btn.clicked.connect(self.accept)
        self.btn.setStyleSheet("margin: 10px 0px 0px 0px;")

        # layout
        self.layout = QVBoxLayout()
        self.message = QLabel(
            "Audio Device not connected? It must be connected in the Snap environment.\n"
            "Run the following command to enable the audio output and restart the application:")
        self.message.setStyleSheet("margin: 10px 0px 10px 0px;")
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.cmd)
        self.layout.addWidget(self.btn)
        self.layout.addStretch()
        self.setLayout(self.layout)
