#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.03 14:55:00                  #
# ================================================== #

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QCursor, QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from pygpt_net.ui.widget.screenshot import ScreenRegionSelector, ScreenshotFlash
from pygpt_net.utils import trans


class Tray:
    REGION_CAPTURE_HIDE_DELAY_MS = 75

    def __init__(self, window=None):
        """
        Tray icon setup

        :param window: Window instance
        """
        self.window = window
        self.is_tray = False
        self.icon = None
        self.region_selector = None
        self.screenshot_flash = None

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

        screenshot_menu = QMenu(trans("menu.tray.screenshot"), w)
        screenshot_menu.setIcon(QIcon(":/icons/computer.svg"))
        tray_menu['screenshot_menu'] = screenshot_menu
        tray_menu['screenshot'] = screenshot_menu.menuAction()

        action = QAction(QIcon(":/icons/crop.svg"), trans("menu.tray.screenshot.select_region"), w)
        tray_menu['screenshot_select_region'] = action
        tray_menu['screenshot_select_region'].triggered.connect(self.select_screenshot_region)
        screenshot_menu.addAction(action)

        action = QAction(QIcon(":/icons/fullscreen.svg"), trans("menu.tray.screenshot.full_screen"), w)
        tray_menu['screenshot_full_screen'] = action
        tray_menu['screenshot_full_screen'].triggered.connect(self.make_screenshot)
        screenshot_menu.addAction(action)

        action = QAction(trans("menu.file.exit"), w)
        action.setIcon(QIcon(":/icons/logout.svg"))
        tray_menu['exit'] = action
        tray_menu['exit'].triggered.connect(app.quit)

        menu = QMenu(w)
        menu.addAction(tray_menu['restore'])
        menu.addAction(tray_menu['new'])
        menu.addAction(tray_menu['scheduled'])
        menu.addAction(tray_menu['open_notepad'])
        menu.addMenu(tray_menu['screenshot_menu'])
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
        """Make a full-screen screenshot and show a short capture flash."""
        path = self.window.controller.painter.capture.screenshot()
        if path:
            self.show_capture_flash(0)
        self.window.restore()
        self.window.controller.chat.common.focus_input()

    def select_screenshot_region(self):
        """Open a fullscreen overlay and let the user select a screenshot region."""
        if self.region_selector is not None:
            self.region_selector.close()
            self.region_selector = None

        selector = ScreenRegionSelector()
        self.region_selector = selector
        screen_geometry = selector.screen_geometry
        screen_index = selector.screen_index

        selector.region_selected.connect(
            lambda region, geometry=screen_geometry, index=screen_index:
            self.make_region_screenshot(region, geometry, index)
        )
        selector.cancelled.connect(self.cancel_region_screenshot)
        selector.show_selector()

    def make_region_screenshot(self, region, screen_geometry, screen_index: int = 0):
        """Capture the selected region after the selector overlay leaves the compositor."""
        self.region_selector = None

        # QWidget.hide() + processEvents() removes the selector from Qt immediately,
        # but the desktop compositor can still expose its previous frame for a short
        # moment. Defer the real screen grab by a few frames so the selection border
        # and dimming overlay cannot leak into the captured image.
        QTimer.singleShot(
            self.REGION_CAPTURE_HIDE_DELAY_MS,
            lambda: self._capture_region_screenshot(region, screen_geometry, screen_index),
        )

    def _capture_region_screenshot(self, region, screen_geometry, screen_index: int = 0):
        """Perform the deferred region capture and restore the application."""
        path = self.window.controller.painter.capture.screenshot_region(
            region,
            screen_geometry,
            screen_index=screen_index,
        )
        if path:
            self.show_capture_flash(screen_index)
        self.window.restore()
        self.window.controller.chat.common.focus_input()

    def show_capture_flash(self, screen_index: int = None):
        """Show a brief fullscreen camera-like flash after a successful capture."""
        screens = QApplication.screens()
        if not screens:
            return

        if screen_index is None:
            screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        else:
            if screen_index < 0 or screen_index >= len(screens):
                screen_index = 0
            screen = screens[screen_index]

        if screen is None:
            return

        flash = ScreenshotFlash(screen)
        self.screenshot_flash = flash
        flash.destroyed.connect(
            lambda _=None, current=flash: self._clear_capture_flash(current)
        )
        flash.show_flash()

    def _clear_capture_flash(self, flash):
        """Clear the current flash reference without clobbering a newer flash."""
        if self.screenshot_flash is flash:
            self.screenshot_flash = None

    def cancel_region_screenshot(self):
        """Clear region selector state after cancellation."""
        self.region_selector = None

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

    def update_schedule_tasks(self, num: int = 0):
        """Update scheduled-tasks tray action and keep it visible while the plugin is enabled."""
        if not self.is_tray:
            return
        action = self.window.ui.tray_menu.get('scheduled')
        if action is None:
            return
        try:
            plugins = self.window.controller.plugins
            if not plugins.is_type_enabled('schedule'):
                self.hide_schedule_menu()
                return
        except (AttributeError, RuntimeError):
            pass
        try:
            count = max(0, int(num or 0))
        except (TypeError, ValueError):
            count = 0
        label = trans("menu.tray.scheduled")
        if count > 0:
            label += f" ({count})"
        action.setText(label)
        if not action.isVisible():
            action.setVisible(True)
