#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

class Debug:
    def __init__(self, window=None):
        """
        Debug controller

        :param window: main window
        """
        self.window = window

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

        # update menu
        self.update_menu()

    def update_menu(self):
        """Updates debug menu"""
        for id in self.window.debugger.ids:
            if id in self.window.debugger.active and self.window.debugger.active[id]:
                self.window.menu['debug.' + id].setChecked(True)
            else:
                self.window.menu['debug.' + id].setChecked(False)
