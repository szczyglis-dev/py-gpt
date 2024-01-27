#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 15:00:00                  #
# ================================================== #

from datetime import datetime

from PySide6.QtGui import QTextCursor


class Debug:
    def __init__(self, window=None):
        """
        Debug controller

        :param window: Window instance
        """
        self.window = window
        self.is_logger = False  # logger window opened

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

    def on_update(self, all: bool = False):
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

    def log(self, data, window: bool = True):
        """
        Log text

        :param data: text to log
        :param window: True if log to window, False if log to console
        """
        if not window:
            print(str(data))
            return

        if not self.is_logger or data is None or data.strip() == '':
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

    def logger_enabled(self):
        """Check if debug window is enabled"""
        return self.is_logger

    def open_logger(self):
        """Open logger dialog"""
        self.window.ui.dialogs.open('logger')
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
            self.window.controller.dialogs.debug.show(id)
            self.on_update(True)

        self.log('debug.' + id + ' toggled')

        # update menu
        self.update()
