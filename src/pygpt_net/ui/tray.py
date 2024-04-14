#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.14 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class Tray:
    def __init__(self, window=None):
        """
        Tray icon setup

        :param window: Window instance
        """
        self.window = window
        self.is_tray = False
        self.icon = None

    def set_icon(self, state: str):
        """
        Set tray icon

        :param state: State name
        """
        if not self.is_tray:
            return

        self.icon.setIcon(
            self.window.ui.get_tray_icon(state)
        )

    def show_msg(self, title: str, msg: str, icon: str = 'Information'):
        """
        Show message

        :param title: Message title
        :param msg: Message
        :param icon: Icon name
        """
        if not self.is_tray:
            return

        self.icon.showMessage(
            "PyGPT: " + title,
            msg,
            getattr(QSystemTrayIcon, icon),
        )

    def setup(self, app=None):
        """
        Setup tray menu

        :param app: QApplication instance
        """
        if not self.window.core.config.get('layout.tray'):
            return

        self.is_tray = True

        self.icon = QSystemTrayIcon(
            self.window.ui.get_tray_icon(self.window.STATE_IDLE),
            app,
        )
        self.icon.setToolTip("PyGPT v{} ({})".format(
            self.window.meta['version'],
            self.window.meta['build']),
        )

        # restore
        action = QAction(trans("action.open"), self.window)
        action.setIcon(QIcon(":/icons/apps.svg"))
        self.window.ui.tray_menu['restore'] = action
        self.window.ui.tray_menu['restore'].triggered.connect(self.window.restore)
        self.window.ui.tray_menu['restore'].setVisible(False)

        # new context
        action = QAction(trans("menu.file.new"), self.window)
        action.setIcon(QIcon(":/icons/add.svg"))
        self.window.ui.tray_menu['new'] = action
        self.window.ui.tray_menu['new'].triggered.connect(self.new_ctx)

        # scheduled tasks
        action = QAction(trans("menu.tray.scheduled"), self.window)
        action.setIcon(QIcon(":/icons/schedule.svg"))
        self.window.ui.tray_menu['scheduled'] = action
        self.window.ui.tray_menu['scheduled'].triggered.connect(self.open_scheduled_tasks)

        # check for updates
        action = QAction(trans("menu.info.updates"), self.window)
        action.setIcon(QIcon(":/icons/public_filled.svg"))
        self.window.ui.tray_menu['update'] = action
        self.window.ui.tray_menu['update'].triggered.connect(self.check_updates)

        # open notepad
        action = QAction(trans("menu.tray.notepad"), self.window)
        action.setIcon(QIcon(":/icons/paste.svg"))
        self.window.ui.tray_menu['open_notepad'] = action
        self.window.ui.tray_menu['open_notepad'].triggered.connect(self.open_notepad)

        if self.window.controller.notepad.get_num_notepads() == 0:
            self.hide_notepad_menu()

        # ask with screenshot
        action = QAction(trans("menu.tray.screenshot"), self.window)
        action.setIcon(QIcon(":/icons/computer.svg"))
        self.window.ui.tray_menu['screenshot'] = action
        self.window.ui.tray_menu['screenshot'].triggered.connect(self.make_screenshot)

        # exit
        action = QAction(trans("menu.file.exit"), self.window)
        action.setIcon(QIcon(":/icons/logout.svg"))
        self.window.ui.tray_menu['exit'] = action
        self.window.ui.tray_menu['exit'].triggered.connect(app.quit)

        menu = QMenu(self.window)
        menu.addAction(self.window.ui.tray_menu['restore'])
        menu.addAction(self.window.ui.tray_menu['new'])
        menu.addAction(self.window.ui.tray_menu['scheduled'])
        menu.addAction(self.window.ui.tray_menu['open_notepad'])
        menu.addAction(self.window.ui.tray_menu['screenshot'])
        menu.addAction(self.window.ui.tray_menu['update'])
        menu.addAction(self.window.ui.tray_menu['exit'])
        self.icon.activated.connect(self.window.tray_toggle)
        self.icon.setContextMenu(menu)
        self.icon.show()

    def new_ctx(self):
        """Create new context"""
        self.window.restore()
        self.window.controller.ctx.new_ungrouped()  # new context without group

    def open_notepad(self):
        """Open notepad"""
        self.window.restore()
        self.window.controller.notepad.open()

    def open_scheduled_tasks(self):
        """Open scheduled tasks"""
        self.window.restore()
        self.window.controller.plugins.settings.open_plugin('crontab')

    def make_screenshot(self):
        """Make screenshot"""
        self.window.controller.painter.capture.screenshot()
        self.window.restore()
        self.window.controller.chat.common.focus_input()

    def check_updates(self):
        """Check for updates"""
        self.window.controller.launcher.check_updates()
        self.window.restore()

    def show_notepad_menu(self):
        """Show notepad menu"""
        if not self.is_tray:
            return
        self.window.ui.tray_menu['open_notepad'].setVisible(True)

    def hide_notepad_menu(self):
        """Hide notepad menu"""
        if not self.is_tray:
            return
        self.window.ui.tray_menu['open_notepad'].setVisible(False)

    def show_schedule_menu(self):
        """Show schedule menu"""
        if not self.is_tray:
            return
        self.window.ui.tray_menu['scheduled'].setVisible(True)

    def hide_schedule_menu(self):
        """Hide schedule menu"""
        if not self.is_tray:
            return
        self.window.ui.tray_menu['scheduled'].setVisible(False)

    def update_schedule_tasks(self, tasks: int = 0):
        """
        Update scheduled jobs number

        :param tasks: Number of scheduled tasks
        """
        if not self.is_tray:
            return
        if tasks > 0:
            info = trans("menu.tray.scheduled") + ": {}".format(tasks)
            self.window.ui.tray_menu['scheduled'].setText(info)
            self.show_schedule_menu()
        else:
            self.hide_schedule_menu()
