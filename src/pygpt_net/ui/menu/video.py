#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.13 19:55:00                  #
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
        """Append video actions to the shared Audio / Video menu."""
        w = self.window
        ui_menu = w.ui.menu
        cam = w.controller.camera
        menu = ui_menu['menu.audio']

        section_video = QAction(trans("menu.audio.section.video"), w)
        section_video.setEnabled(False)
        section_font = section_video.font()
        section_font.setBold(True)
        section_video.setFont(section_font)

        capture = QAction(trans("menu.video.capture"), w, checkable=True)
        capture.setToolTip(trans('vision.capture.enable.tooltip'))
        capture.triggered.connect(cam.toggle)

        capture_auto = QAction(trans("menu.video.capture.auto"), w, checkable=True)
        capture_auto.setToolTip(trans('vision.capture.auto.tooltip'))
        capture_auto.triggered.connect(cam.toggle_auto)

        menu.addSeparator()
        menu.addAction(section_video)
        menu.addSeparator()
        menu.addActions([capture, capture_auto])
        menu.setToolTipsVisible(True)

        ui_menu['menu.audio.section.video'] = section_video
        ui_menu['video.capture'] = capture
        ui_menu['video.capture.auto'] = capture_auto
