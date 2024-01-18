#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.18 10:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from pygpt_net.utils import trans


class Tray:
    def __init__(self, window=None):
        """
        Tray icon setup

        :param window: Window instance
        """
        self.window = window

    def setup(self, app=None):
        """
        Setup tray menu

        :param app: QApplication instance
        """
        tray = QSystemTrayIcon(self.window.ui.get_app_icon(), app)
        tray.setToolTip("PyGPT v{}".format(self.window.meta['version']))
        menu = QMenu()
        tray_menu = {}
        tray_menu['new'] = menu.addAction(trans("menu.file.new"))
        tray_menu['new'].triggered.connect(self.new_ctx)
        tray_menu['update'] = menu.addAction(trans("menu.info.updates"))
        tray_menu['update'].triggered.connect(self.window.controller.launcher.check_updates)

        # open notepad
        if self.window.controller.notepad.get_num_notepads() > 0:
            tray_menu['open_notepad'] = menu.addAction(trans("menu.tray.notepad"))
            tray_menu['open_notepad'].triggered.connect(self.open_notepad)

        tray_menu['exit'] = menu.addAction(trans("menu.file.exit"))
        tray_menu['exit'].triggered.connect(app.quit)
        tray.setContextMenu(menu)
        tray.show()

    def new_ctx(self):
        """Create new context"""
        self.window.controller.ctx.new()
        self.window.activateWindow()  # focus window

    def open_notepad(self):
        """Open notepad"""
        self.window.controller.notepad.open()
