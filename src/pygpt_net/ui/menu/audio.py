#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.05 12:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon

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
        self.window.ui.menu['audio.control.plugin'] = QAction(
            trans("menu.audio.control.plugin"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['audio.control.global'] = QAction(
            trans("menu.audio.control.global"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['audio.cache.clear'] = QAction(
            QIcon(":/icons/delete.svg"),
            trans("menu.audio.cache.clear"),
            self.window,
            checkable=False,
        )

        self.window.ui.menu['audio.output'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('audio_output')
        )
        self.window.ui.menu['audio.input'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('audio_input')
        )
        self.window.ui.menu['audio.control.plugin'].triggered.connect(
            lambda: self.window.controller.plugins.toggle('voice_control')
        )
        self.window.ui.menu['audio.control.global'].triggered.connect(
            lambda: self.window.controller.access.voice.toggle_voice_control()
        )
        self.window.ui.menu['audio.cache.clear'].triggered.connect(
            lambda: self.window.controller.audio.clear_cache()
        )

        self.window.ui.menu['menu.audio'] = self.window.menuBar().addMenu(trans("menu.audio"))
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.input'])
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.output'])
        self.window.ui.menu['menu.audio'].addSeparator()
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.control.plugin'])
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.control.global'])
        self.window.ui.menu['menu.audio'].addSeparator()
        self.window.ui.menu['menu.audio'].addAction(self.window.ui.menu['audio.cache.clear'])
