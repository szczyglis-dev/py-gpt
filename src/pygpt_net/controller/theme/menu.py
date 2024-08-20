#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.24 02:00:00                  #
# ================================================== #

from pygments.styles import get_all_styles
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
        self.syntax_loaded = False
        self.density_loaded = False

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

    def setup_syntax(self):
        """Setup syntax menu"""
        styles = self.window.controller.chat.render.web_renderer.highlight.get_styles()
        styles.sort()
        # clear menu
        for style in self.window.ui.menu['theme_syntax']:
            self.window.ui.menu['theme.syntax'].removeAction(self.window.ui.menu['theme_syntax'][style])
        # setup syntax menu
        for style in styles:
            self.window.ui.menu['theme_syntax'][style] = QAction(style, self.window, checkable=True)
            self.window.ui.menu['theme_syntax'][style].triggered.connect(
                lambda checked=None, style=style: self.window.controller.theme.toggle_syntax(style, update_menu=True))
            self.window.ui.menu['theme.syntax'].addAction(self.window.ui.menu['theme_syntax'][style])

    def setup_density(self):
        """Setup menu list"""
        if self.density_loaded:
            return
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
        self.density_loaded = True

    def update_density(self):
        """Update layout density menu"""
        current_density = self.window.core.config.get('layout.density')
        for value in self.density_values:
            self.window.ui.menu['theme.layout.density'][value].setChecked(False)
            if value == current_density:
                self.window.ui.menu['theme.layout.density'][value].setChecked(True)

    def update_list(self):
        """Update theme list menu"""
        current = self.window.core.config.get('theme')
        for theme in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][theme].setChecked(False)
        if current in self.window.ui.menu['theme']:
            self.window.ui.menu['theme'][current].setChecked(True)

    def update_syntax(self):
        """Update syntax menu"""
        current = self.window.core.config.get('render.code_syntax')
        for style in self.window.ui.menu['theme_syntax']:
            self.window.ui.menu['theme_syntax'][style].setChecked(False)
        if current in self.window.ui.menu['theme_syntax']:
            self.window.ui.menu['theme_syntax'][current].setChecked(True)
