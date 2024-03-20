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

from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans
import pygpt_net.icons_rc

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
            QIcon(":/icons/video.svg"),
            trans("menu.tools.media.player"),
            self.window,
            checkable=False,
        )
        self.window.ui.menu['tools.media.player'].triggered.connect(self.window.tools.player.toggle)

        # audio transcribe
        self.window.ui.menu['tools.audio.transcribe'] = QAction(
            QIcon(":/icons/hearing.svg"),
            trans("menu.tools.audio.transcribe"),
            self.window,
            checkable=False,
        )
        self.window.ui.menu['tools.audio.transcribe'].triggered.connect(self.window.tools.transcriber.toggle)

        # image viewer
        self.window.ui.menu['tools.image.viewer'] = QAction(
            QIcon(":/icons/image.svg"),
            trans("menu.tools.image.viewer"),
            self.window,
            checkable=False,
        )
        self.window.ui.menu['tools.image.viewer'].triggered.connect(
            lambda: self.window.tools.viewer.open_preview()
        )

        # text editor
        self.window.ui.menu['tools.text.editor'] = QAction(
            QIcon(":/icons/edit.svg"),
            trans("menu.tools.text.editor"),
            self.window,
            checkable=False,
        )
        self.window.ui.menu['tools.text.editor'].triggered.connect(
            lambda: self.window.tools.editor.open()
        )

        # code interpreter
        self.window.ui.menu['tools.interpreter'] = QAction(
            QIcon(":/icons/code.svg"),
            trans("menu.tools.interpreter"),
            self.window,
            checkable=False,
        )
        self.window.ui.menu['tools.interpreter'].triggered.connect(self.window.tools.interpreter.toggle)

        self.window.ui.menu['menu.tools'] = self.window.menuBar().addMenu(trans("menu.tools"))
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.media.player'])
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.image.viewer'])
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.text.editor'])
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.audio.transcribe'])
        self.window.ui.menu['menu.tools'].addAction(self.window.ui.menu['tools.interpreter'])

