#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.19 01:00:00                  #
# ================================================== #

import webbrowser


class Info:
    def __init__(self, window=None):
        """
        Info dialogs controller

        :param window: Window instance
        """
        self.window = window

        # prepare info ids
        self.ids = ['about', 'changelog', 'license']
        self.active = {}

        # prepare active
        for id in self.ids:
            self.active[id] = False

    def setup(self):
        pass

    def toggle(self, id: str, width: int = 400, height: int = 400):
        """
        Toggle info dialog

        :param id: dialog to toggle
        :param width: dialog width
        :param height: dialog height
        """
        if id in self.active and self.active[id]:
            self.window.ui.dialogs.close('info.' + id)
            self.active[id] = False
        else:
            if id == 'about':
                self.window.ui.dialogs.about.prepare()
            self.window.ui.dialogs.open(
                'info.' + id,
                width=width,
                height=height,
            )
            self.active[id] = True

        # update menu
        self.update_menu()

    def goto_website(self):
        """Open project website"""
        webbrowser.open(self.window.meta['website'])

    def goto_docs(self):
        """Open docs"""
        webbrowser.open(self.window.meta['docs'])

    def goto_pypi(self):
        """Open PyPi"""
        webbrowser.open(self.window.meta['pypi'])

    def goto_github(self):
        """Open GitHub page"""
        webbrowser.open(self.window.meta['github'])

    def goto_snap(self):
        """Open Snapcraft page"""
        webbrowser.open(self.window.meta['snap'])

    def goto_update(self):
        """Open update URL"""
        webbrowser.open(self.window.meta['website'])

    def goto_donate(self):
        """Open donate page"""
        webbrowser.open(self.window.meta['donate'])

    def goto_discord(self):
        """Open discord page"""
        webbrowser.open(self.window.meta['discord'])

    def update_menu(self):
        """Update info menu"""
        for id in self.ids:
            if id in self.active and self.active[id]:
                self.window.ui.menu['info.' + id].setChecked(True)
            else:
                self.window.ui.menu['info.' + id].setChecked(False)
