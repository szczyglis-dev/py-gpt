#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 06:00:00                  #
# ================================================== #
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QCheckBox

from pygpt_net.ui.widget.dialog.audio import AudioTranscribeDialog
from pygpt_net.ui.widget.textarea.editor import CodeEditor
from pygpt_net.utils import trans


class AudioTranscribe:
    def __init__(self, window=None):
        """
        Audio Transcribe dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup transcribe dialog"""
        id = 'audio.transcribe'

        self.window.ui.editor[id] = CodeEditor(self.window)
        self.window.ui.editor[id].setReadOnly(False)
        self.window.ui.editor[id].setProperty('class', 'code-editor')

        self.window.ui.nodes['audio.transcribe.convert_video'] = QCheckBox(trans("audio.transcribe.auto_convert"))
        self.window.ui.nodes['audio.transcribe.convert_video'].setChecked(True)
        self.window.ui.nodes['audio.transcribe.convert_video'].clicked.connect(
            lambda: self.window.controller.audio.toggle_auto_convert_video()
        )

        self.window.ui.nodes['audio.transcribe.clear'] = QPushButton(trans("dialog.logger.btn.clear"))
        self.window.ui.nodes['audio.transcribe.clear'].clicked.connect(
            lambda: self.clear()
        )

        self.window.ui.nodes['audio.transcribe.open'] = QPushButton(trans("audio.transcribe.open"))
        self.window.ui.nodes['audio.transcribe.open'].clicked.connect(
            lambda: self.window.controller.audio.open_transcribe_file())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['audio.transcribe.clear'])
        bottom_layout.addWidget(self.window.ui.nodes['audio.transcribe.open'])

        self.window.ui.nodes['audio.transcribe.title'] = QLabel(trans("audio.transcribe.tip"))
        self.window.ui.nodes['audio.transcribe.status'] = QLabel("...")
        self.window.ui.nodes['audio.transcribe.status'].setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['audio.transcribe.title'])
        layout.addWidget(self.window.ui.editor[id])
        layout.addLayout(bottom_layout)
        layout.addWidget(self.window.ui.nodes['audio.transcribe.convert_video'])
        layout.addWidget(self.window.ui.nodes['audio.transcribe.status'])

        self.window.ui.dialog['audio.transcribe'] = AudioTranscribeDialog(self.window)
        self.window.ui.dialog['audio.transcribe'].setLayout(layout)
        self.window.ui.dialog['audio.transcribe'].setWindowTitle(trans("audio.transcribe.title"))


    def clear(self):
        """Clear transcribe dialog"""
        self.window.controller.audio.transcribe_clear()