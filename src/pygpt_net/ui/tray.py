#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction
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

        # new context
        self.window.ui.tray_menu['new'] = QAction(trans("menu.file.new"), self.window)
        self.window.ui.tray_menu['new'].triggered.connect(self.new_ctx)

        # scheduled tasks
        self.window.ui.tray_menu['scheduled'] = QAction(trans("menu.tray.scheduled"), self.window)
        self.window.ui.tray_menu['scheduled'].triggered.connect(self.open_scheduled_tasks)

        # check for updates
        self.window.ui.tray_menu['update'] = QAction(trans("menu.info.updates"), self.window)
        self.window.ui.tray_menu['update'].triggered.connect(self.check_updates)

        # open notepad
        self.window.ui.tray_menu['open_notepad'] = QAction(trans("menu.tray.notepad"), self.window)
        self.window.ui.tray_menu['open_notepad'].triggered.connect(self.open_notepad)

        if self.window.controller.notepad.get_num_notepads() == 0:
            self.hide_notepad_menu()

        # ask with screenshot
        self.window.ui.tray_menu['screenshot'] = QAction(trans("menu.tray.screenshot"), self.window)
        self.window.ui.tray_menu['screenshot'].triggered.connect(self.make_screenshot)

        self.window.ui.tray_menu['exit'] = QAction(trans("menu.file.exit"), self.window)
        self.window.ui.tray_menu['exit'].triggered.connect(app.quit)

        menu = QMenu(self.window)
        menu.addAction(self.window.ui.tray_menu['new'])
        menu.addAction(self.window.ui.tray_menu['scheduled'])
        menu.addAction(self.window.ui.tray_menu['update'])
        menu.addAction(self.window.ui.tray_menu['open_notepad'])
        menu.addAction(self.window.ui.tray_menu['screenshot'])
        menu.addAction(self.window.ui.tray_menu['exit'])

        tray.setContextMenu(menu)
        tray.show()

    def new_ctx(self):
        """Create new context"""
        self.window.controller.ctx.new()
        self.window.activateWindow()

    def open_notepad(self):
        """Open notepad"""
        self.window.controller.notepad.open()

    def make_screenshot(self):
        """Make screenshot"""
        self.window.controller.painter.capture.screenshot()
        self.window.activateWindow()
        self.window.controller.chat.common.focus_input()

    def check_updates(self):
        """Check for updates"""
        self.window.controller.launcher.check_updates()
        self.window.activateWindow()

    def show_notepad_menu(self):
        """Show notepad menu"""
        self.window.ui.tray_menu['open_notepad'].setVisible(True)

    def hide_notepad_menu(self):
        """Hide notepad menu"""
        self.window.ui.tray_menu['open_notepad'].setVisible(False)

    def show_schedule_menu(self):
        """Show schedule menu"""
        self.window.ui.tray_menu['scheduled'].setVisible(True)

    def hide_schedule_menu(self):
        """Hide schedule menu"""
        self.window.ui.tray_menu['scheduled'].setVisible(False)

    def update_schedule_tasks(self, tasks: int = 0):
        """Update scheduled jobs number"""
        if tasks > 0:
            info = trans("menu.tray.scheduled") + ": {}".format(tasks)
            self.window.ui.tray_menu['scheduled'].setText(info)
            self.show_schedule_menu()
        else:
            self.hide_schedule_menu()

    def open_scheduled_tasks(self):
        """Open scheduled tasks"""
        self.window.controller.plugins.settings.open_plugin('crontab')
        self.window.activateWindow()
