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


class Video:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup video menu"""
        self.window.ui.menu['video.capture'] = QAction(
            trans("menu.video.capture"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['video.capture'].setToolTip(trans('vision.capture.enable.tooltip'))
        self.window.ui.menu['video.capture'].triggered.connect(
            lambda: self.window.controller.camera.toggle(self.window.ui.menu['video.capture'].isChecked())
        )

        self.window.ui.menu['video.capture.auto'] = QAction(
            trans("menu.video.capture.auto"),
            self.window,
            checkable=True,
        )
        self.window.ui.menu['video.capture.auto'].setToolTip(trans('vision.capture.auto.tooltip'))
        self.window.ui.menu['video.capture.auto'].triggered.connect(
            lambda: self.window.controller.camera.toggle_auto(self.window.ui.menu['video.capture.auto'].isChecked())
        )

        self.window.ui.menu['menu.video'] = self.window.menuBar().addMenu(trans("menu.video"))
        self.window.ui.menu['menu.video'].addAction(self.window.ui.menu['video.capture'])
        self.window.ui.menu['menu.video'].addAction(self.window.ui.menu['video.capture.auto'])
        self.window.ui.menu['menu.video'].setToolTipsVisible(True)
