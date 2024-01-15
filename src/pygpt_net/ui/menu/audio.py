#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 03:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction

from pygpt_net.utils import trans


class Audio:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup audio menu"""
        self.window.ui.menu['audio.output.azure'] = QAction(trans("menu.audio.output.azure"),
                                                            self.window, checkable=True)
        self.window.ui.menu['audio.output.tts'] = QAction(trans("menu.audio.output.tts"),
                                                          self.window, checkable=True)
        self.window.ui.menu['audio.input.whisper'] = QAction(trans("menu.audio.input.whisper"),
                                                             self.window, checkable=True)

        self.window.ui.menu['audio.output.azure'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('audio_azure'))
        self.window.ui.menu['audio.output.tts'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('audio_openai_tts'))
        self.window.ui.menu['audio.input.whisper'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('audio_openai_whisper'))

        self.window.ui.menu['menu.audio'] = self.window.menuBar().addMenu(trans("menu.audio"))
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.output.azure'])
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.output.tts'])
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.input.whisper'])
