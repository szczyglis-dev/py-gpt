#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

import webbrowser


class Info:
    def __init__(self, window=None):
        """
        Info controller

        :param window main window
        """
        self.window = window

    def setup(self):
        pass

    def toggle(self, id):
        """
        Toggles info window

        :param id: window to toggle
        """
        if id in self.window.info.active and self.window.info.active[id]:
            self.window.ui.dialogs.close('info.' + id)
            self.window.info.active[id] = False
        else:
            self.window.ui.dialogs.open('info.' + id)
            self.window.info.active[id] = True

        # update menu
        self.update_menu()

    def goto_website(self):
        """Opens project website"""
        webbrowser.open(self.window.website)

    def goto_github(self):
        """Opens GitHub page"""
        webbrowser.open(self.window.github)

    def goto_update(self):
        """Opens update URL"""
        webbrowser.open(self.window.website)

    def update_menu(self):
        """Updates info menu"""
        for id in self.window.info.ids:
            if id in self.window.info.active and self.window.info.active[id]:
                self.window.menu['info.' + id].setChecked(True)
            else:
                self.window.menu['info.' + id].setChecked(False)
