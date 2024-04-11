#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.11 02:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction


class Menu:
    def __init__(self, window=None):
        """
        Theme menu controller

        :param window: Window instance
        """
        self.window = window
        self.density_values = [-2, -1, 0, 1, 2]
        self.loaded = False

    def setup_list(self):
        """Setup menu list"""
        # setup themes list menu
        if self.loaded:
            return
        themes = self.window.controller.theme.common.get_themes_list()
        for theme in themes:
            name = self.window.controller.theme.common.translate(theme)
            self.window.ui.menu['theme'][theme] = QAction(name, self.window, checkable=True)
            self.window.ui.menu['theme'][theme].triggered.connect(
                lambda checked=None, theme=theme: self.window.controller.theme.toggle(theme))

            # append to dark or light menu
            if theme.startswith('dark'):
                self.window.ui.menu['theme.dark'].addAction(self.window.ui.menu['theme'][theme])
            elif theme.startswith('light'):
                self.window.ui.menu['theme.light'].addAction(self.window.ui.menu['theme'][theme])
        self.loaded = True

    def setup_density(self):
        """Setup menu list"""
        # setup layout density menu
        current_density = self.window.core.config.get('layout.density')
        for value in self.density_values:
            name = str(value)
            if value > 0:
                name = '+' + name
            self.window.ui.menu['theme.layout.density'][value] = QAction(name, self.window, checkable=True)
            self.window.ui.menu['theme.layout.density'][value].triggered.connect(
                lambda checked=None, value=value: self.window.controller.theme.toggle_option('layout.density', value))
            self.window.ui.menu['theme.density'].addAction(self.window.ui.menu['theme.layout.density'][value])
            if value == current_density:
                self.window.ui.menu['theme.layout.density'][value].setChecked(True)

    def update_density(self):
        """Update layout density menu"""
        current_density = self.window.core.config.get('layout.density')
        for value in self.density_values:
            self.window.ui.menu['theme.layout.density'][value].setChecked(False)
            if value == current_density:
                self.window.ui.menu['theme.layout.density'][value].setChecked(True)

    def update_list(self):
        """Update theme list menu"""
        for theme in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][theme].setChecked(False)
        current = self.window.core.config.get('theme')
        if current in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][current].setChecked(True)
