#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.16 20:00:00                  #
# ================================================== #
from datetime import datetime


class Debug:
    def __init__(self, window=None):
        """
        Debug controller

        :param window: main window
        """
        self.window = window
        self.is_logger = False

    def log(self, data):
        """
        Logs text

        :param text: text to log
        """
        if not self.is_logger:
            return
        # prepend log with timestamp
        txt = datetime.now().strftime('%H:%M:%S') + ' ' + str(data)
        self.window.logger.appendPlainText(txt)

    def logger_close(self):
        """Closes logger"""
        self.window.ui.dialogs.close('logger')
        self.is_logger = False
        self.update()

    def logger_open(self):
        """Opens logger"""
        self.window.ui.dialogs.open('logger')
        self.is_logger = True
        self.update()

    def logger_toggle(self):
        """Toggles logger"""
        if self.is_logger:
            self.logger_close()
        else:
            self.logger_open()

    def logger_clear(self):
        """Clears logger"""
        self.window.logger.clear()

    def toggle(self, id):
        """
        Toggles debug window

        :param id: window to toggle
        """
        if id in self.window.debugger.active and self.window.debugger.active[id]:
            self.window.ui.dialogs.close('debug.' + id)
            self.window.debugger.active[id] = False
        else:
            self.window.ui.dialogs.open('debug.' + id)
            self.window.debugger.active[id] = True
            self.window.debugger.update(True)

        self.window.log('debug.' + id + ' toggled')

        # update menu
        self.update()

    def update_menu(self):
        """Updates debug menu"""
        for id in self.window.debugger.ids:
            if id in self.window.debugger.active and self.window.debugger.active[id]:
                self.window.menu['debug.' + id].setChecked(True)
            else:
                self.window.menu['debug.' + id].setChecked(False)

        if self.is_logger:
            self.window.menu['debug.logger'].setChecked(True)
        else:
            self.window.menu['debug.logger'].setChecked(False)

    def update(self):
        """Updates debug"""
        self.update_menu()
