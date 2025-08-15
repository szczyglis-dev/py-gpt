#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.16 00:00:00                  #
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
        self.icon.setIcon(self.window.ui.get_tray_icon(state))

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
            f"PyGPT: {title}",
            msg,
            getattr(QSystemTrayIcon, icon, QSystemTrayIcon.Information),
        )

    def setup(self, app=None):
        """
        Setup tray menu

        :param app: QApplication instance
        """
        if not self.window.core.config.get('layout.tray'):
            return
        if self.is_tray and self.icon is not None:
            return

        self.is_tray = True
        w = self.window
        ui = w.ui
        tray_menu = ui.tray_menu

        self.icon = QSystemTrayIcon(
            ui.get_tray_icon(w.STATE_IDLE),
            app,
        )
        self.icon.setToolTip(f"PyGPT {w.meta['version']} ({w.meta['build'].replace('.', '-')})")

        action = QAction(trans("action.open"), w)
        action.setIcon(QIcon(":/icons/apps.svg"))
        tray_menu['restore'] = action
        tray_menu['restore'].triggered.connect(w.restore)
        tray_menu['restore'].setVisible(False)

        action = QAction(trans("menu.file.new"), w)
        action.setIcon(QIcon(":/icons/add.svg"))
        tray_menu['new'] = action
        tray_menu['new'].triggered.connect(self.new_ctx)

        action = QAction(trans("menu.tray.scheduled"), w)
        action.setIcon(QIcon(":/icons/schedule.svg"))
        tray_menu['scheduled'] = action
        tray_menu['scheduled'].triggered.connect(self.open_scheduled_tasks)

        action = QAction(trans("menu.info.updates"), w)
        action.setIcon(QIcon(":/icons/public_filled.svg"))
        tray_menu['update'] = action
        tray_menu['update'].triggered.connect(self.check_updates)

        action = QAction(trans("menu.tray.notepad"), w)
        action.setIcon(QIcon(":/icons/paste.svg"))
        tray_menu['open_notepad'] = action
        tray_menu['open_notepad'].triggered.connect(self.open_notepad)

        if w.controller.notepad.get_num_notepads() == 0:
            self.hide_notepad_menu()

        action = QAction(trans("menu.tray.screenshot"), w)
        action.setIcon(QIcon(":/icons/computer.svg"))
        tray_menu['screenshot'] = action
        tray_menu['screenshot'].triggered.connect(self.make_screenshot)

        action = QAction(trans("menu.file.exit"), w)
        action.setIcon(QIcon(":/icons/logout.svg"))
        tray_menu['exit'] = action
        tray_menu['exit'].triggered.connect(app.quit)

        menu = QMenu(w)
        menu.addAction(tray_menu['restore'])
        menu.addAction(tray_menu['new'])
        menu.addAction(tray_menu['scheduled'])
        menu.addAction(tray_menu['open_notepad'])
        menu.addAction(tray_menu['screenshot'])
        menu.addAction(tray_menu['update'])
        menu.addAction(tray_menu['exit'])
        self.icon.activated.connect(w.tray_toggle)
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
        action = self.window.ui.tray_menu.get('open_notepad')
        if action and not action.isVisible():
            action.setVisible(True)

    def hide_notepad_menu(self):
        """Hide notepad menu"""
        if not self.is_tray:
            return
        action = self.window.ui.tray_menu.get('open_notepad')
        if action and action.isVisible():
            action.setVisible(False)

    def show_schedule_menu(self):
        """Show schedule menu"""
        if not self.is_tray:
            return
        action = self.window.ui.tray_menu.get('scheduled')
        if action and not action.isVisible():
            action.setVisible(True)

    def hide_schedule_menu(self):
        """Hide schedule menu"""
        if not self.is_tray:
            return
        action = self.window.ui.tray_menu.get('scheduled')
        if action and action.isVisible():
            action.setVisible(False)

    def update_schedule_tasks(self, tasks: int = 0):
        """
        Update scheduled jobs number

        :param tasks: Number of scheduled tasks
        """
        if not self.is_tray:
            return
        if tasks > 0:
            action = self.window.ui.tray_menu['scheduled']
            info = f"{trans('menu.tray.scheduled')}: {tasks}"
            if action.text() != info:
                action.setText(info)
            self.show_schedule_menu()
        else:
            self.hide_schedule_menu()