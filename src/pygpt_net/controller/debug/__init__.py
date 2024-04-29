#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 07:00:00                  #
# ================================================== #

from datetime import datetime
from logging import ERROR, WARNING, INFO, DEBUG

from PySide6.QtCore import Slot
from PySide6.QtGui import QTextCursor


class Debug:
    def __init__(self, window=None):
        """
        Debug controller

        :param window: Window instance
        """
        self.window = window
        self.is_logger = False  # logger window opened
        self.is_app_log = False  # app log window opened
        self.allow_level_change = False  # allow changing log level

    def update(self):
        """Update debug"""
        self.update_menu()

    def update_menu(self):
        """Update debug menu"""
        for id in self.window.controller.dialogs.debug.get_ids():
            if self.window.controller.dialogs.debug.is_active(id):
                self.window.ui.menu['debug.' + id].setChecked(True)
            else:
                self.window.ui.menu['debug.' + id].setChecked(False)

        if self.is_logger:
            self.window.ui.menu['debug.logger'].setChecked(True)
        else:
            self.window.ui.menu['debug.logger'].setChecked(False)

        if self.is_app_log:
            self.window.ui.menu['debug.app.log'].setChecked(True)
        else:
            self.window.ui.menu['debug.app.log'].setChecked(False)

    def toggle_menu(self):
        """Toggle debug menu"""
        stage = self.window.core.config.get('debug')
        self.window.ui.menu['menu.debug'].menuAction().setVisible(stage)

    def set_log_level(self, level: str = 'error'):
        """
        Switch logging level in runtime

        :param level: log level (debug, info, warning, error), default: error
        """
        if not self.allow_level_change:
            return

        print("[LOGGER] Changing log level to: " + level)

        if level == 'debug':
            self.window.core.debug.switch_log_level(DEBUG)
            print("** DEBUG level enabled")
        elif level == 'info':
            self.window.core.debug.switch_log_level(INFO)
            print("** INFO level enabled")
        elif level == 'warning':
            self.window.core.debug.switch_log_level(WARNING)
            print("** WARNING level enabled")
        else:
            self.window.core.debug.switch_log_level(ERROR)
            print("** ERROR level enabled")

        self.window.ui.dialogs.app_log.update_log_level()

    def on_post_update(self, all: bool = False):
        """
        Update debug windows (only if active)

        :param all: update all debug windows
        """
        # not_realtime = ['context']
        not_realtime = []
        for id in self.window.controller.dialogs.debug.get_ids():
            if self.window.controller.dialogs.debug.is_active(id):
                if all or id not in not_realtime:
                    self.window.controller.dialogs.debug.update_worker(id)

    def post_setup(self):
        """Post setup debug"""
        self.connect_signals()

    def setup(self):
        """Setup debug"""
        current = self.window.core.debug.get_log_level()
        if current == ERROR:
            self.allow_level_change = True
        else:
            return
        # switch log level if set in config
        if self.window.core.config.has('log.level'):
            level = self.window.core.config.get('log.level')
            if level != "error":
                print("[LOGGER] Started with log level: " + self.window.core.debug.get_log_level_name())
                print("[LOGGER] Switching to: " + level)
                self.set_log_level(level)

    def connect_signals(self):
        """Connect signals"""
        # webengine debug signals
        if self.window.controller.chat.render.get_engine() == "web":
            signals = self.window.controller.chat.render.web_renderer.get_output_node().page().signals
            signals.js_message.connect(self.handle_js_message)

    @Slot(int, str, str)
    def handle_js_message(self, line_number: int, message: str, source_id: str):
        """
        Handle JS message

        :param line_number: line number
        :param message: message
        :param source_id: source ID
        """
        data = "[JS] Line " + str(line_number) + ": " + message
        self.log(data, window=True)

    @Slot(object)
    def handle_log(self, data: any):
        """
        Handle log message

        :param data: message to log
        """
        self.log(data)

    def log(self, data: any, window: bool = True):
        """
        Log message to console or logger window

        :param data: text to log
        :param window: True if log to window, False if log to console
        """
        if not window:
            print(str(data))
            return

        if not self.is_logger or data is None or str(data).strip() == "":
            return

        data = datetime.now().strftime('%H:%M:%S.%f') + ': ' + str(data)
        cur = self.window.logger.textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(data) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertText("\n")
        self.window.logger.setTextCursor(cur)  # Update visible cursor

    def logger_enabled(self) -> bool:
        """
        Check if debug window is enabled

        :return: True if enabled, False otherwise
        """
        return self.is_logger

    def open_logger(self):
        """Open logger dialog"""
        self.window.ui.dialogs.open('logger', width=800, height=600)
        self.is_logger = True
        self.update()

    def close_logger(self):
        """Close logger dialog"""
        self.window.ui.dialogs.close('logger')
        self.is_logger = False
        self.update()

    def toggle_logger(self):
        """Toggle logger dialog"""
        if self.is_logger:
            self.close_logger()
        else:
            self.open_logger()

    def clear_logger(self):
        """Clear logger dialog"""
        self.window.logger.clear()

    def toggle(self, id: str):
        """
        Toggle debug window

        :param id: debug window to toggle
        """
        if self.window.controller.dialogs.debug.is_active(id):
            self.window.controller.dialogs.debug.hide(id)
        else:
            if id == "db":
                self.window.ui.dialogs.database.viewer.update_table_view()  # update view on load
            self.window.controller.dialogs.debug.show(id)
            self.on_post_update(True)

        self.log('debug.' + id + ' toggled')

        # update menu
        self.update()

    def toggle_app_log(self):
        """
        Toggle app log window
        """
        id = 'app.log'
        if self.is_app_log:
            self.window.ui.dialogs.close(id)
            self.is_app_log = False
        else:
            self.window.ui.dialogs.open(id, width=800, height=600)
            self.window.ui.dialogs.app_log.reload()
            self.is_app_log = True

        self.log('debug.' + id + ' toggled')

        # update menu
        self.update()

    def reload(self):
        """Reload debug"""
        self.toggle_menu()
        self.update()
