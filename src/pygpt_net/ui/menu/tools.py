#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.20 06:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction

from pygpt_net.utils import trans


class Tools:
    def __init__(self, window=None):
        """
        Tools menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup tools menu"""
        # media player
        self.window.ui.menu['tools.media.player'] = QAction(
            trans("menu.tools.media.player"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['tools.media.player'].triggered.connect(
            lambda: self.window.tools.player.show_hide(self.window.ui.menu['tools.media.player'].isChecked())
        )

        # audio transcribe
        self.window.ui.menu['tools.audio.transcribe'] = QAction(
            trans("menu.tools.audio.transcribe"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['tools.audio.transcribe'].triggered.connect(
            lambda: self.window.tools.transcriber.show_hide(
                self.window.ui.menu['tools.audio.transcribe'].isChecked())
        )

        # code interpreter
        self.window.ui.menu['tools.interpreter'] = QAction(
            trans("menu.tools.interpreter"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['tools.interpreter'].triggered.connect(
            lambda: self.window.tools.interpreter.show_hide(
                self.window.ui.menu['tools.interpreter'].isChecked())
        )

        # text editor
        self.window.ui.menu['tools.text.editor'] = QAction(
            trans("menu.tools.text.editor"),
            self.window,
            checkable=False,
        )
        self.window.ui.menu['tools.text.editor'].triggered.connect(
            lambda: self.window.tools.editor.open()
        )

        self.window.ui.menu['menu.tools'] = self.window.menuBar().addMenu(trans("menu.tools"))
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.media.player'])
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.audio.transcribe'])
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.interpreter'])
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.text.editor'])
        # self.window.ui.menu['menu.tools'].setToolTipsVisible(True)
