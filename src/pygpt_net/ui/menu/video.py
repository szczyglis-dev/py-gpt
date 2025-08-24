#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
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
        w = self.window
        ui_menu = w.ui.menu
        cam = w.controller.camera

        capture = QAction(trans("menu.video.capture"), w, checkable=True)
        capture.setToolTip(trans('vision.capture.enable.tooltip'))
        capture.triggered.connect(cam.toggle)

        capture_auto = QAction(trans("menu.video.capture.auto"), w, checkable=True)
        capture_auto.setToolTip(trans('vision.capture.auto.tooltip'))
        capture_auto.triggered.connect(cam.toggle_auto)

        menu_video = w.menuBar().addMenu(trans("menu.video"))
        menu_video.addActions([capture, capture_auto])
        menu_video.setToolTipsVisible(True)

        ui_menu['video.capture'] = capture
        ui_menu['video.capture.auto'] = capture_auto
        ui_menu['menu.video'] = menu_video