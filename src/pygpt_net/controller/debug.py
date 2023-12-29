#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
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
        self.is_logger = False

    def update(self):
        """Update debug"""
        self.update_menu()

    def update_menu(self):
        """Update debug menu"""
        for id in self.window.core.debug.ids:
            if id in self.window.core.debug.active and self.window.core.debug.active[id]:
                self.window.ui.menu['debug.' + id].setChecked(True)
            else:
                self.window.ui.menu['debug.' + id].setChecked(False)

        if self.is_logger:
            self.window.ui.menu['debug.logger'].setChecked(True)
        else:
            self.window.ui.menu['debug.logger'].setChecked(False)

    def log(self, data, window=True):
        """
        Log text

        :param data: text to log
        :param window: true if log to all plugins (enabled or not)
        """
        if not window:
            print(str(data))
            return

        if not self.is_logger or data is None or data.strip() == '':
            return

        # prepend log with timestamp
        data = datetime.now().strftime('%H:%M:%S') + ': ' + str(data)
        # append log to logger
        txt = self.window.logger.toPlainText()
        if txt.strip() != '':
            txt += '\n'
        txt += data
        self.window.logger.setPlainText(txt)
        # set cursor to end
        self.window.logger.moveCursor(QTextCursor.End)

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

    def toggle(self, id):
        """
        Toggle debug window

        :param id: debug window to toggle
        """
        if id in self.window.core.debug.active and self.window.core.debug.active[id]:
            self.window.ui.dialogs.close('debug.' + id)
            self.window.core.debug.active[id] = False
        else:
            self.window.ui.dialogs.open('debug.' + id)
            self.window.core.debug.active[id] = True
            self.window.core.debug.on_update(True)

        self.log('debug.' + id + ' toggled')

        # update menu
        self.update()
