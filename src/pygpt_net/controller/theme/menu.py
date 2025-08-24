#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QActionGroup


class Menu:
    def __init__(self, window=None):
        """
        Theme menu controller

        :param window: Window instance
        """
        self.window = window
        self.density_values = (-2, -1, 0, 1, 2)
        self.loaded = False
        self.syntax_loaded = False
        self.density_loaded = False

        self._style_group = None
        self._theme_group = None
        self._density_group = None
        self._syntax_group = None

    def _on_style_triggered(self, action):
        """
        Handle style change triggered by menu action

        :param action: QAction instance
        """
        self.window.controller.theme.toggle_style(action.data())

    def _on_theme_triggered(self, action):
        """
        Handle theme change triggered by menu action

        :param action: QAction instance
        """
        self.window.controller.theme.toggle_theme_by_menu(action.data())

    def _on_syntax_triggered(self, action):
        """
        Handle syntax highlight change triggered by menu action

        :param action: QAction instance
        """
        self.window.controller.theme.toggle_syntax(action.data(), update_menu=True)

    def _on_density_triggered(self, action):
        """
        Handle layout density change triggered by menu action

        :param action: QAction instance
        """
        self.window.controller.theme.toggle_option_by_menu('layout.density', action.data())

    def setup_list(self):
        """Setup menu list"""
        if self.loaded:
            return

        w = self.window
        menu = w.ui.menu
        common = w.controller.theme.common

        if self._style_group is None:
            self._style_group = QActionGroup(w)
            self._style_group.setExclusive(True)
            self._style_group.triggered.connect(self._on_style_triggered)

        styles = common.get_styles_list()
        menu_style_dict = menu['theme_style']
        menu_style = menu['theme.style']
        for style in styles:
            style_id = style.lower()
            title = style.replace('_', ' ').title()
            if title == "Chatgpt":
                title = "ChatGPT"
            elif title == "Chatgpt Wide":
                title = "ChatGPT (wide)"
            act = QAction(title, w, checkable=True)
            act.setData(style_id)
            menu_style_dict[style_id] = act
            self._style_group.addAction(act)
            menu_style.addAction(act)

        if self._theme_group is None:
            self._theme_group = QActionGroup(w)
            self._theme_group.setExclusive(True)
            self._theme_group.triggered.connect(self._on_theme_triggered)

        themes = common.get_themes_list()
        themes += common.get_custom_themes_list()
        themes.sort()

        menu_theme_dict = menu['theme']
        menu_dark = menu['theme.dark']
        menu_light = menu['theme.light']
        for theme in themes:
            name = common.translate(theme)
            act = QAction(name, w, checkable=True)
            act.setData(theme)
            menu_theme_dict[theme] = act
            self._theme_group.addAction(act)
            if theme.startswith('dark'):
                menu_dark.addAction(act)
            elif theme.startswith('light'):
                menu_light.addAction(act)

        self.loaded = True

    def setup_syntax(self):
        """Setup syntax menu"""
        w = self.window
        menu = w.ui.menu

        styles = w.controller.chat.render.web_renderer.body.highlight.get_styles()
        styles.sort()

        if self.syntax_loaded:
            existing = sorted(menu['theme_syntax'].keys())
            if existing == styles:
                return

        menu_syntax_dict = menu['theme_syntax']
        menu_syntax = menu['theme.syntax']

        for act in menu_syntax_dict.values():
            menu_syntax.removeAction(act)
            act.deleteLater()
        menu_syntax_dict.clear()

        if self._syntax_group is None:
            self._syntax_group = QActionGroup(w)
            self._syntax_group.setExclusive(True)
            self._syntax_group.triggered.connect(self._on_syntax_triggered)

        for style in styles:
            act = QAction(style, w, checkable=True)
            act.setData(style)
            menu_syntax_dict[style] = act
            self._syntax_group.addAction(act)
            menu_syntax.addAction(act)

        self.syntax_loaded = True

    def setup_density(self):
        """Setup menu list"""
        if self.density_loaded:
            return

        w = self.window
        menu = w.ui.menu

        if self._density_group is None:
            self._density_group = QActionGroup(w)
            self._density_group.setExclusive(True)
            self._density_group.triggered.connect(self._on_density_triggered)

        current_density = w.core.config.get('layout.density')
        menu_density_dict = menu['theme.layout.density']
        menu_density = menu['theme.density']

        for value in self.density_values:
            name = str(value)
            if value > 0:
                name = '+' + name
            act = QAction(name, w, checkable=True)
            act.setData(value)
            menu_density_dict[value] = act
            self._density_group.addAction(act)
            menu_density.addAction(act)
            if value == current_density:
                act.setChecked(True)

        self.density_loaded = True

    def update_density(self):
        """Update layout density menu"""
        current_density = self.window.core.config.get('layout.density')
        items = self.window.ui.menu['theme.layout.density']
        act = items.get(current_density)
        if act is not None:
            act.setChecked(True)
        else:
            for a in items.values():
                a.setChecked(False)

    def update_list(self):
        """Update theme list menu"""
        current_style = self.window.core.config.get('theme.style')
        style_items = self.window.ui.menu['theme_style']
        act = style_items.get(current_style)
        if act is not None:
            act.setChecked(True)
        else:
            for a in style_items.values():
                a.setChecked(False)

        current_theme = self.window.core.config.get('theme')
        theme_items = self.window.ui.menu['theme']
        act = theme_items.get(current_theme)
        if act is not None:
            act.setChecked(True)
        else:
            for a in theme_items.values():
                a.setChecked(False)

    def update_syntax(self):
        """Update code syntax highlight menu"""
        current = self.window.core.config.get('render.code_syntax')
        items = self.window.ui.menu['theme_syntax']
        act = items.get(current)
        if act is not None:
            act.setChecked(True)
        else:
            for a in items.values():
                a.setChecked(False)