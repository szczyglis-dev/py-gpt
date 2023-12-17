#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

import webbrowser


class Info:
    def __init__(self, window=None):
        """
        Info controller

        :param window Window instance
        """
        self.window = window

    def setup(self):
        pass

    def toggle(self, id):
        """
        Toggle info window

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
        """Open project website"""
        webbrowser.open(self.window.website)

    def goto_docs(self):
        """Open docs"""
        webbrowser.open(self.window.docs)

    def goto_pypi(self):
        """Open PyPi"""
        webbrowser.open(self.window.pypi)

    def goto_github(self):
        """Open GitHub page"""
        webbrowser.open(self.window.github)

    def goto_update(self):
        """Open update URL"""
        webbrowser.open(self.window.website)

    def update_menu(self):
        """Update info menu"""
        for id in self.window.info.ids:
            if id in self.window.info.active and self.window.info.active[id]:
                self.window.menu['info.' + id].setChecked(True)
            else:
                self.window.menu['info.' + id].setChecked(False)
