#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 18:00:00                  #
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
        self.window.ui.menu['audio.output'] = QAction(
            trans("menu.audio.output"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['audio.input'] = QAction(
            trans("menu.audio.input"),
            self.window,
            checkable=True,
        )

        self.window.ui.menu['audio.output'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('audio_output')
        )
        self.window.ui.menu['audio.input'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('audio_input')
        )
        self.window.ui.menu['menu.audio'] = self.window.menuBar().addMenu(trans("menu.audio"))
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.input'])
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.output'])
